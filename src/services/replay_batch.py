"""Profit Replay batch runner — Core5 + WIN/WDO (13.0-beta)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.logging_config import get_logger
from src.services.filipe_universe import CORE5_STOCKS
from src.services.futures_universe import symbol_list as futures_symbols
from src.services.replay_engine import start_replay

logger = get_logger(__name__)

STOCK_STRATEGIES = (
    "s1_vwap_reclaim",
    "s2_orb_break",
    "s3_bb_fade",
    "s4_arch_bias",
    "s5_pulse",
)
WIN_STRATEGIES = (
    "f1_open_drive",
    "f2_vwap_reclaim",
    "f3_lunch_fade",
    "f4_afternoon_trend",
    "f5_failed_breakout",
)


def replay_universe() -> list[str]:
    return list(CORE5_STOCKS) + futures_symbols()


def strategies_for_symbol(symbol: str) -> tuple[str, ...]:
    sym = symbol.upper()
    if sym.startswith("WIN") or sym.startswith("WDO"):
        return WIN_STRATEGIES
    return STOCK_STRATEGIES


def run_replay_batch(
    session: Session,
    *,
    symbols: list[str] | None = None,
    auto_promote: bool = True,
    speed: float = 10.0,
) -> dict[str, Any]:
    """Run replay training for each symbol × strategy template; optional WFO promote."""
    settings = get_settings()
    syms = [s.strip().upper() for s in (symbols or replay_universe()) if s.strip()]
    results: list[dict[str, Any]] = []
    errors: list[str] = []

    for sym in syms:
        for strat in strategies_for_symbol(sym):
            try:
                out = start_replay(
                    strategy=strat,
                    symbol=sym,
                    speed=speed,
                    mode="training",
                    session=session,
                )
                results.append(
                    {
                        "symbol": sym,
                        "strategy": strat,
                        "status": out.get("status"),
                        "job_id": out.get("job_id"),
                        "fill_count": out.get("fill_count"),
                    }
                )
            except Exception as exc:
                logger.exception("replay_batch_item_failed", symbol=sym, strategy=strat)
                errors.append(f"{sym}/{strat}: {exc}")

    promotion: dict[str, Any] | None = None
    if auto_promote and settings.walk_forward_auto_promote:
        from src.services.walk_forward_promotion import run_walk_forward_promotion

        try:
            promotion = run_walk_forward_promotion(
                session, folds=settings.walk_forward_promote_folds
            )
        except Exception as exc:
            errors.append(f"wfo_promote: {exc}")

    session.commit()
    return {
        "symbols": syms,
        "runs": len(results),
        "results": results,
        "promotion": promotion,
        "errors": errors,
    }
