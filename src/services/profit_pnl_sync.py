"""Profit P&L sync stub — periodic refresh from bridge/journal (4.0-alpha)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.logging_config import get_logger
from src.services.pnl_truth import resolve_day_pnl

logger = get_logger(__name__)

_last_snapshot: dict | None = None


def sync_profit_pnl(session: Session) -> dict:
    """Resolve day P&L and cache last snapshot for health/debug."""
    global _last_snapshot
    snapshot = resolve_day_pnl(session)
    _last_snapshot = snapshot
    logger.info(
        "profit_pnl_sync",
        day_pnl=snapshot["day_pnl"],
        source=snapshot["pnl_source"],
        trades_today=snapshot["trades_today"],
    )
    return snapshot


def last_pnl_snapshot() -> dict | None:
    return _last_snapshot
