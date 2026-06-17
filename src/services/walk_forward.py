"""Walk-forward optimization — rolling train/test windows on Python backtest layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.logging_config import get_logger
from src.models import OptimizationRun, Strategy
from src.services.backtest import BacktestService

logger = get_logger(__name__)


class WalkForwardOptimizer:
    """Simple walk-forward: split synthetic bars into folds, optimize on train, validate on test."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.backtest = BacktestService(session)

    def run(
        self,
        strategy: Strategy,
        symbol: str,
        parameter_space: dict[str, list[Any]],
        folds: int = 3,
    ) -> OptimizationRun:
        import itertools

        run = OptimizationRun(
            strategy_id=strategy.id,
            method="walk_forward",
            status="running",
            parameter_space={"space": parameter_space, "folds": folds, "symbol": symbol},
        )
        self.session.add(run)
        self.session.commit()

        keys = list(parameter_space.keys())
        values = [parameter_space[k] for k in keys]
        fold_results: list[dict[str, Any]] = []
        best_params: dict[str, Any] | None = None
        best_avg_test_pnl = float("-inf")

        try:
            for fold_idx in range(folds):
                train_seed = 42 + fold_idx * 1000
                test_seed = train_seed + 500

                best_fold: dict[str, Any] | None = None
                for combo in itertools.product(*values):
                    params = dict(zip(keys, combo))
                    strategy.parameters = params
                    train_bt = self.backtest.run_python_backtest(
                        strategy, symbol, bars=200, seed=train_seed
                    )
                    test_bt = self.backtest.run_python_backtest(
                        strategy, symbol, bars=100, seed=test_seed
                    )
                    train_pnl = (train_bt.metrics or {}).get("net_pnl", 0)
                    test_pnl = (test_bt.metrics or {}).get("net_pnl", 0)
                    entry = {
                        "parameters": params,
                        "train_pnl": train_pnl,
                        "test_pnl": test_pnl,
                    }
                    if best_fold is None or train_pnl > best_fold["train_pnl"]:
                        best_fold = entry

                if best_fold:
                    fold_results.append(
                        {
                            "fold": fold_idx + 1,
                            "best_parameters": best_fold["parameters"],
                            "train_pnl": best_fold["train_pnl"],
                            "test_pnl": best_fold["test_pnl"],
                        }
                    )
                    if best_fold["test_pnl"] > best_avg_test_pnl:
                        best_avg_test_pnl = best_fold["test_pnl"]
                        best_params = best_fold["parameters"]

            run.status = "completed"
            run.results = {"folds": fold_results, "fold_count": folds}
            run.best_parameters = best_params
            if best_params:
                strategy.parameters = best_params
                final_bt = self.backtest.run_python_backtest(strategy, symbol, seed=99)
                run.best_metrics = final_bt.metrics
            run.completed_at = datetime.utcnow()
        except Exception as exc:
            run.status = "failed"
            run.results = {"error": str(exc)}
            logger.error("walk_forward_failed", error=str(exc))

        self.session.commit()
        return run
