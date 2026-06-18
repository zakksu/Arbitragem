"""Replay training for top archaeology symbols (11.0-beta A11.7)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.logging_config import get_logger
from src.services.archaeology_backtest import build_archaeology_summary
from src.services.archaeology_fifo import trade_lane
from src.services.replay_batch import run_replay_batch, strategies_for_symbol
from src.services.structure_types import replay_strategy_for_structure

logger = get_logger(__name__)

_DEFAULT_STRUCTURES = {
    "cash": "stock_scalp_vwap",
    "futures": "opening_range_break",
    "options": "mean_reversion_band",
}


def top_archaeology_symbols(session: Session, *, limit: int = 10) -> list[str]:
    body = build_archaeology_summary(session, limit=limit)
    symbols = [row["symbol"] for row in body.get("top_symbols") or [] if row.get("symbol")]
    if symbols:
        return symbols[:limit]
    fallback = body.get("top_symbols") or []
    return [str(row.get("symbol", "")).upper() for row in fallback if row.get("symbol")][:limit]


def default_strategy_for_symbol(symbol: str) -> str:
    lane = trade_lane(symbol)
    structure = _DEFAULT_STRUCTURES.get(lane, "scalp")
    return replay_strategy_for_structure(structure)


def run_archaeology_replay_batch(
    session: Session,
    *,
    limit: int = 10,
    speed: float = 10.0,
    auto_promote: bool = False,
    symbols: list[str] | None = None,
) -> dict[str, Any]:
    """Replay top archaeology names — one primary strategy per symbol."""
    syms = [s.strip().upper() for s in (symbols or top_archaeology_symbols(session, limit=limit)) if s.strip()]
    if not syms:
        return {"symbols": [], "runs": 0, "results": [], "errors": ["no_archaeology_symbols"]}

    results: list[dict[str, Any]] = []
    errors: list[str] = []
    from src.services.replay_engine import start_replay

    for sym in syms:
        strat = default_strategy_for_symbol(sym)
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
                    "lane": trade_lane(sym),
                    "strategy": strat,
                    "status": out.get("status"),
                    "job_id": out.get("job_id"),
                    "fill_count": out.get("fill_count"),
                }
            )
        except Exception as exc:
            logger.exception("archaeology_replay_failed", symbol=sym)
            errors.append(f"{sym}: {exc}")

    promotion = None
    if auto_promote:
        from src.config import get_settings

        if get_settings().walk_forward_auto_promote:
            from src.services.walk_forward_promotion import run_walk_forward_promotion

            try:
                promotion = run_walk_forward_promotion(session, folds=get_settings().walk_forward_promote_folds)
            except Exception as exc:
                errors.append(f"wfo_promote: {exc}")

    session.commit()
    return {
        "symbols": syms,
        "runs": len(results),
        "results": results,
        "promotion": promotion,
        "errors": errors,
        "strategies_available": {s: list(strategies_for_symbol(s)) for s in syms},
    }
