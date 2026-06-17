"""Paper graduation gates per symbol (10.0-rc)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.models import Trade
from src.services.pnl_reconcile import reconcile_symbol_pnl
from src.services.symbol_factory import factory_status, get_symbol_patch_config
from src.services.trust_scorecard import build_trust_scorecard


def graduation_status(session: Session, symbol: str) -> dict[str, Any]:
    sym = symbol.strip().upper()
    settings = get_settings()

    fills = (
        session.query(Trade)
        .filter(Trade.symbol == sym, Trade.source.in_(["replay", "paper", "profit", "clear"]))
        .count()
    )
    reconcile = reconcile_symbol_pnl(session, sym)
    trust = build_trust_scorecard(session)
    factory = factory_status(session)
    in_motor = sym in [s.upper() for s in factory.get("motor_symbols", [])]

    trust_score = float(trust.get("score") or trust.get("trust_score") or 0)
    gates = {
        "min_fills": fills >= 5,
        "reconcile_green": reconcile.get("status") == "green",
        "trust_85": trust_score >= 85,
        "in_motor_or_golden": in_motor or sym == settings.golden_path_symbol,
    }
    graduated = all(gates.values())
    return {
        "symbol": sym,
        "graduated": graduated,
        "gates": gates,
        "fill_count": fills,
        "trust_score": trust_score,
        "reconcile": reconcile,
        "patch_config": get_symbol_patch_config(sym),
        "auto_execute_allowed": graduated and settings.paper_trading_mode,
    }
