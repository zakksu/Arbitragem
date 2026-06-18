"""Pro trade journal desk — SMB / prop-shop blotter (13.0-rc)."""

from __future__ import annotations

import csv
import io
from datetime import datetime, time, timedelta
from typing import Any

from sqlalchemy.orm import Session

from src.config import PROJECT_ROOT, get_settings
from src.models import Trade, TradeIdea
from src.services.motor_journal import list_today
from src.services.pnl_truth import resolve_day_pnl


def _load_win_archaeology() -> dict[str, Any]:
    path = PROJECT_ROOT / "data" / ".dev" / "b3_history_insights.json"
    if not path.exists():
        return {}
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        top = data.get("summary", {}).get("top_symbols") or []
        win_rows = [(s, n) for s, n in top if str(s).upper().startswith("WIN")]
        return {
            "win_trade_count": sum(n for _, n in win_rows),
            "top_win_series": win_rows[:8],
            "futures_count": data.get("summary", {}).get("futures_count"),
            "note": "Historical WIN mini index — enable Cross Order in Profit for WINFUT",
        }
    except (OSError, ValueError, TypeError):
        return {}


def _grade_trade(pnl: float | None, fees: float) -> str:
    if pnl is None:
        return "—"
    net = pnl - fees
    if net >= 50:
        return "A"
    if net >= 10:
        return "B"
    if net >= 0:
        return "C"
    if net >= -30:
        return "D"
    return "F"


def build_trade_journal_desk(
    session: Session,
    *,
    days: int = 30,
    range_key: str | None = None,
    symbol: str | None = None,
    setup_tag: str | None = None,
) -> dict[str, Any]:
    """Aggregate trades, ideas, motor log, archaeology for board partial."""
    settings = get_settings()
    now = datetime.utcnow()
    if range_key == "today":
        since = datetime.combine(now.date(), time.min)
        days = 1
    elif range_key == "5d":
        since = now - timedelta(days=5)
        days = 5
    else:
        since = datetime.combine((now - timedelta(days=days)).date(), time.min)

    q = session.query(Trade).filter(Trade.executed_at >= since)
    if symbol:
        q = q.filter(Trade.symbol == symbol.strip().upper())
    trades = q.order_by(Trade.executed_at.desc()).limit(200).all()

    tag_symbols: set[str] | None = None
    if setup_tag:
        tag = setup_tag.strip().lower()
        tagged = (
            session.query(TradeIdea)
            .filter(TradeIdea.created_at >= since)
            .order_by(TradeIdea.created_at.desc())
            .limit(200)
            .all()
        )
        tag_symbols = {
            i.symbol.upper()
            for i in tagged
            if any(str(t).lower() == tag for t in (i.rationale_tags or []))
        }
        if tag_symbols:
            trades = [t for t in trades if t.symbol.upper() in tag_symbols]

    ideas_q = session.query(TradeIdea).filter(TradeIdea.created_at >= since)
    if symbol:
        ideas_q = ideas_q.filter(TradeIdea.symbol == symbol.strip().upper())
    ideas = ideas_q.order_by(TradeIdea.created_at.desc()).limit(100).all()
    if setup_tag and tag_symbols is not None:
        ideas = [i for i in ideas if i.symbol.upper() in tag_symbols]
    truth = resolve_day_pnl(session)
    motor = list_today(session, limit=60)

    blotter: list[dict[str, Any]] = []
    gross = 0.0
    fees = 0.0
    wins = 0
    for t in trades:
        pnl = float(t.pnl or 0)
        fee = float(t.fees or 0)
        gross += pnl
        fees += fee
        if pnl > 0:
            wins += 1
        blotter.append(
            {
                "id": t.id,
                "time": t.executed_at.strftime("%Y-%m-%d %H:%M") if t.executed_at else "",
                "symbol": t.symbol,
                "side": t.side,
                "qty": t.quantity,
                "price": t.price,
                "fees_brl": fee,
                "pnl_brl": pnl,
                "net_brl": round(pnl - fee, 2),
                "grade": _grade_trade(pnl, fee),
                "source": t.source,
                "note": (t.journal_note or "")[:120],
            }
        )

    idea_rows = [
        {
            "id": i.id,
            "symbol": i.symbol,
            "status": i.status,
            "structure": i.structure_type,
            "side": i.side,
            "reliability": i.reliability,
            "tags": i.rationale_tags or [],
        }
        for i in ideas[:40]
    ]

    n = len(trades) or 1
    return {
        "days": days,
        "range_key": range_key or f"{days}d",
        "filters": {
            "symbol": symbol.upper() if symbol else None,
            "setup_tag": setup_tag,
            "range_key": range_key,
        },
        "capital_brl": settings.paper_capital_brl if settings.paper_trading_mode else settings.live_capital_brl,
        "paper_mode": settings.paper_trading_mode,
        "summary": {
            "trade_count": len(trades),
            "gross_pnl_brl": round(gross, 2),
            "fees_brl": round(fees, 2),
            "net_pnl_brl": round(gross - fees, 2),
            "win_rate_pct": round(wins / n * 100, 1),
            "day_pnl_brl": truth.get("day_pnl") or truth.get("journal_pnl"),
            "expectancy_brl": round((gross - fees) / n, 2),
        },
        "blotter": blotter,
        "ideas": idea_rows,
        "motor_log": motor,
        "win_archaeology": _load_win_archaeology(),
    }


def export_journal_csv(session: Session, *, days: int = 90) -> str:
    desk = build_trade_journal_desk(session, days=days)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "time",
            "symbol",
            "side",
            "quantity",
            "price",
            "fees_brl",
            "pnl_brl",
            "net_brl",
            "grade",
            "source",
            "note",
        ]
    )
    for row in desk["blotter"]:
        w.writerow(
            [
                row["time"],
                row["symbol"],
                row["side"],
                row["qty"],
                row["price"],
                row["fees_brl"],
                row["pnl_brl"],
                row["net_brl"],
                row["grade"],
                row["source"],
                row["note"],
            ]
        )
    return buf.getvalue()


def patch_trade_note(session: Session, trade_id: int, note: str | None) -> dict[str, Any]:
    """Update journal note on a trade row (14.0 GA journal pro)."""
    trade = session.get(Trade, trade_id)
    if not trade:
        raise ValueError("Trade not found")
    trade.journal_note = (note or "").strip()[:2000] or None
    session.commit()
    session.refresh(trade)
    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "journal_note": trade.journal_note,
        "ok": True,
    }
