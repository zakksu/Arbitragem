"""Walk-forward optimizer facade for autonomous engine."""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.orm import Session

from src.models import Strategy
from src.services.walk_forward import WalkForwardOptimizer
from src.services.walk_forward_promotion import DEFAULT_PARAMETER_SPACE, PROMOTE_SYMBOLS

DEFAULT_FOLDS = 3


class AutonomousOptimizer:
    def __init__(self, session: Session) -> None:
        self.session = session
        self._wf = WalkForwardOptimizer(session)

    def run_wfo_sync(
        self,
        strategy: Strategy,
        symbol: str,
        *,
        folds: int = DEFAULT_FOLDS,
    ) -> dict[str, Any]:
        run = self._wf.run(strategy, symbol, DEFAULT_PARAMETER_SPACE, folds=folds)
        return {
            "run_id": run.id,
            "status": run.status,
            "symbol": symbol,
            "best_parameters": run.best_parameters,
            "best_metrics": run.best_metrics,
            "results": run.results,
        }

    async def run_wfo_batch(
        self,
        strategies: list[Strategy],
        symbols: list[str] | None = None,
        *,
        folds: int = DEFAULT_FOLDS,
    ) -> list[dict[str, Any]]:
        syms = symbols or list(PROMOTE_SYMBOLS)[:3]
        out: list[dict[str, Any]] = []

        def _batch() -> list[dict[str, Any]]:
            rows: list[dict[str, Any]] = []
            for strategy in strategies:
                for sym in syms:
                    try:
                        rows.append(self.run_wfo_sync(strategy, sym, folds=folds))
                    except Exception as exc:
                        rows.append({"symbol": sym, "status": "failed", "error": str(exc)})
            return rows

        return await asyncio.to_thread(_batch)
