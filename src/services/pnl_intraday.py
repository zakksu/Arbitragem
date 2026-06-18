"""Intraday PnL series + session projection (14.0-beta)."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.models import Trade
from src.services.pnl_truth import resolve_day_pnl
from src.services.risk_summary import build_risk_summary
from src.services.trade_journal_desk import build_trade_journal_desk
from src.services.trading_orchestrator import b3_session_open


def _lane_key(symbol: str) -> str:
    sym = (symbol or "").upper()
    if sym.startswith("WIN") or sym.startswith("WDO"):
        return "win"
    if len(sym) > 6 or sym.endswith("X") or sym.endswith("Y"):
        return "opt"
    return "cash"


def build_intraday_pnl(session: Session) -> dict[str, Any]:
    """Minute-bucket cumulative net PnL for today (API + PnL tab)."""
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    trades = (
        session.query(Trade)
        .filter(Trade.executed_at >= today_start)
        .order_by(Trade.executed_at.asc())
        .all()
    )
    day = resolve_day_pnl(session)
    cumulative = 0.0
    buckets: list[dict[str, Any]] = [
        {"ts": today_start.isoformat(), "cumulative_brl": 0.0, "fees_brl": 0.0}
    ]
    lanes: dict[str, float] = {"cash": 0.0, "win": 0.0, "opt": 0.0}
    bucket_by_minute: dict[str, dict[str, Any]] = {today_start.strftime("%Y-%m-%d %H:%M"): buckets[0]}

    for t in trades:
        pnl = float(t.pnl or 0)
        fees = float(t.fees or 0)
        net = pnl - fees
        cumulative += net
        lane = _lane_key(t.symbol)
        lanes[lane] = round(lanes.get(lane, 0.0) + net, 2)
        minute_key = (t.executed_at or today_start).strftime("%Y-%m-%d %H:%M")
        bucket_by_minute[minute_key] = {
            "ts": (t.executed_at or today_start).isoformat(),
            "cumulative_brl": round(cumulative, 2),
            "fees_brl": round(fees, 2),
            "symbol": t.symbol,
        }

    buckets = list(bucket_by_minute.values())
    return {
        "buckets": buckets,
        "points": buckets,
        "day_pnl_brl": day["day_pnl"],
        "trades_today": day["trades_today"],
        "pnl_source": day["pnl_source"],
        "lanes": lanes,
        "updated_at": datetime.utcnow().isoformat(),
    }


def build_pnl_projection(session: Session) -> dict[str, Any]:
    """Simple expectancy model — labeled estimate, not ML."""
    desk = build_trade_journal_desk(session, days=30)
    expectancy = float(desk["summary"].get("expectancy_brl") or 0)
    day_pnl = float(desk["summary"].get("day_pnl_brl") or 0)
    settings = get_settings()

    now = datetime.utcnow()
    session_open = b3_session_open()
    session_end = datetime.combine(now.date(), time(20, 0))
    minutes_left = max(0, int((session_end - now).total_seconds() / 60)) if session_open else 0
    cycle_min = max(1, int(settings.effective_paper_orchestrator_interval_sec / 60) or 1)
    trades_est = minutes_left / cycle_min if session_open else 0
    projected = round(day_pnl + expectancy * trades_est, 2)
    vol = abs(expectancy) * 2.5

    return {
        "expectancy_brl": round(expectancy, 2),
        "day_pnl_brl": round(day_pnl, 2),
        "session_open": session_open,
        "session_remaining_min": minutes_left,
        "estimated_trades_remaining": round(trades_est, 1),
        "projected_eod_brl": projected,
        "projected_eod_low_brl": round(projected - vol, 2),
        "projected_eod_high_brl": round(projected + vol, 2),
        "model": "expectancy_estimate",
        "label": "Expectancy × est. trades remaining (not guaranteed)",
    }


def build_pnl_tab_payload(session: Session) -> dict[str, Any]:
    """Template context for pnl_tab.html partial + SSE stream."""
    intraday = build_intraday_pnl(session)
    projection = build_pnl_projection(session)
    risk = build_risk_summary(session)
    risk["max_daily_loss_brl"] = risk.get("tightest_loss_limit_brl") or risk.get(
        "default_loss_limit_brl", 0
    )
    lanes_raw = intraday["lanes"]
    total_abs = sum(abs(v) for v in lanes_raw.values()) or 1.0
    lanes = {
        **lanes_raw,
        "cash_pct": round(abs(lanes_raw.get("cash", 0)) / total_abs * 100, 1),
        "win_pct": round(abs(lanes_raw.get("win", 0)) / total_abs * 100, 1),
        "opt_pct": round(abs(lanes_raw.get("opt", 0)) / total_abs * 100, 1),
    }
    limit = float(risk.get("tightest_loss_limit_brl") or 0)
    day_pnl = float(intraday["day_pnl_brl"])
    stop_remaining = max(0.0, limit + day_pnl) if day_pnl < 0 else limit

    return {
        "intraday": intraday,
        "projection": projection,
        "risk": risk,
        "day_pnl_brl": day_pnl,
        "lanes": lanes,
        "stop_loss_budget": round(stop_remaining, 2),
        "projection_label": projection.get("label"),
    }
