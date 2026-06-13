"""Aggregate risk snapshot for dashboard — day P&L, limits, paper mode."""

from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.config import get_settings
from src.integrations.clear_api import get_clear_client
from src.models import Strategy, Trade


def build_risk_summary(session: Session) -> dict:
    settings = get_settings()
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

    strategies = session.query(Strategy).all()
    active = [s for s in strategies if s.status == "active"]
    tightest_limit = min(
        (s.daily_loss_limit_brl for s in strategies),
        default=settings.default_daily_loss_limit_brl,
    )

    account = get_clear_client().get_account_summary()
    broker_day_pnl = float(account.get("day_pnl", 0) or 0)
    day_pnl = float(journal_pnl or 0) if journal_pnl else broker_day_pnl

    loss_used_pct = 0.0
    if tightest_limit > 0 and day_pnl < 0:
        loss_used_pct = min(100.0, abs(day_pnl) / tightest_limit * 100)

    status = "ok"
    if day_pnl <= -tightest_limit:
        status = "blocked"
    elif loss_used_pct >= 80:
        status = "warning"

    return {
        "paper_trading_mode": settings.paper_trading_mode,
        "day_pnl": round(day_pnl, 2),
        "broker_day_pnl": round(broker_day_pnl, 2),
        "journal_pnl": round(float(journal_pnl or 0), 2),
        "trades_today": int(trade_count or 0),
        "active_strategies": len(active),
        "total_strategies": len(strategies),
        "default_loss_limit_brl": settings.default_daily_loss_limit_brl,
        "tightest_loss_limit_brl": tightest_limit,
        "loss_limit_used_pct": round(loss_used_pct, 1),
        "max_contracts_default": settings.default_max_contracts,
        "status": status,
        "can_start_new_strategy": status != "blocked",
    }
