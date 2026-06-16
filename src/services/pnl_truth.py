"""Single source of truth for session day P&L across Profit, journal, Clear."""

from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.integrations.clear_api import get_clear_client
from src.integrations.profit_bridge import get_profit_client
from src.models import Trade


def _journal_day_pnl(session: Session) -> tuple[float, int]:
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    journal_pnl = (
        session.query(func.coalesce(func.sum(Trade.pnl), 0.0))
        .filter(Trade.executed_at >= today_start, Trade.pnl.isnot(None))
        .scalar()
    )
    trade_count = (
        session.query(func.count(Trade.id))
        .filter(Trade.executed_at >= today_start)
        .scalar()
    )
    return float(journal_pnl or 0), int(trade_count or 0)


def _profit_day_pnl() -> float | None:
    client = get_profit_client()
    if not client.is_available():
        return None
    summary = client.get_account_summary()
    if summary and summary.get("day_pnl") is not None:
        return float(summary["day_pnl"])
    trades = client.get_trades_today()
    if not trades:
        return None
    realized = sum(float(t.pnl or 0) for t in trades if t.pnl is not None)
    return realized


def resolve_day_pnl(session: Session) -> dict:
    """Pick authoritative day P&L: journal > Profit bridge > Clear mock."""
    journal_pnl, trades_today = _journal_day_pnl(session)
    profit_pnl = _profit_day_pnl()
    clear_account = get_clear_client().get_account_summary()
    clear_pnl = float(clear_account.get("day_pnl", 0) or 0)

    if trades_today > 0:
        day_pnl = journal_pnl
        source = "journal"
    elif profit_pnl is not None:
        day_pnl = profit_pnl
        source = "profit"
    else:
        day_pnl = clear_pnl
        source = "clear"

    return {
        "day_pnl": round(day_pnl, 2),
        "journal_pnl": round(journal_pnl, 2),
        "profit_day_pnl": round(profit_pnl, 2) if profit_pnl is not None else None,
        "broker_day_pnl": round(clear_pnl, 2),
        "pnl_source": source,
        "trades_today": trades_today,
    }
