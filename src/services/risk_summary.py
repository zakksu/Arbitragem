"""Aggregate risk snapshot for dashboard — day P&L, limits, paper mode."""

from __future__ import annotations

from datetime import datetime, time

from sqlalchemy.orm import Session

from src.config import get_settings
from src.models import Strategy
from src.services.kill_switch import status as kill_switch_status
from src.services.pnl_truth import resolve_day_pnl
from src.services.risk_profile import get_or_create_profile


def build_risk_summary(session: Session) -> dict:
    settings = get_settings()
    profile = get_or_create_profile(session)
    pnl = resolve_day_pnl(session)
    day_pnl = pnl["day_pnl"]
    journal_pnl = pnl["journal_pnl"]
    broker_day_pnl = pnl["broker_day_pnl"]
    trade_count = pnl["trades_today"]

    strategies = session.query(Strategy).all()
    active = [s for s in strategies if s.status == "active"]
    profile_limit = profile.max_daily_loss_brl
    tightest_limit = min(
        (s.daily_loss_limit_brl for s in strategies),
        default=profile_limit,
    )
    tightest_limit = min(tightest_limit, profile_limit)

    loss_used_pct = 0.0
    if tightest_limit > 0 and day_pnl < 0:
        loss_used_pct = min(100.0, abs(day_pnl) / tightest_limit * 100)

    status = "ok"
    if day_pnl <= -tightest_limit:
        status = "blocked"
    elif loss_used_pct >= 80:
        status = "warning"

    ks = kill_switch_status()
    can_trade = status != "blocked" and not ks["active"]

    return {
        "paper_trading_mode": settings.paper_trading_mode,
        "day_pnl": day_pnl,
        "broker_day_pnl": broker_day_pnl,
        "journal_pnl": journal_pnl,
        "profit_day_pnl": pnl.get("profit_day_pnl"),
        "pnl_source": pnl["pnl_source"],
        "trades_today": trade_count,
        "active_strategies": len(active),
        "total_strategies": len(strategies),
        "default_loss_limit_brl": profile_limit,
        "tightest_loss_limit_brl": tightest_limit,
        "loss_limit_used_pct": round(loss_used_pct, 1),
        "max_contracts_default": settings.default_max_contracts,
        "status": status,
        "can_start_new_strategy": can_trade,
        "kill_switch_active": ks["active"],
        "kill_switch_reason": ks.get("reason"),
        "can_confirm_ideas": can_trade,
        "can_execute_ideas": can_trade,
    }
