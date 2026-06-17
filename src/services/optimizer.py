"""Autonomous optimization — grid search and genetic algorithm (Python layer)."""

from __future__ import annotations

import itertools
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.logging_config import get_logger
from src.models import OptimizationRun, Strategy
from src.services.backtest import BacktestService

logger = get_logger(__name__)


class OptimizerService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.backtest = BacktestService(session)

    def run_grid_search(
        self,
        strategy: Strategy,
        symbol: str,
        parameter_space: dict[str, list[Any]],
    ) -> OptimizationRun:
        run = OptimizationRun(
            strategy_id=strategy.id,
            method="grid",
            status="running",
            parameter_space=parameter_space,
        )
        self.session.add(run)
        self.session.commit()

        keys = list(parameter_space.keys())
        values = [parameter_space[k] for k in keys]
        results: list[dict[str, Any]] = []
        best: dict[str, Any] | None = None

        from src.services.resource_profile import get_resource_profile

        prof = get_resource_profile()
        max_combos = 16 if prof.low_ram else 10_000
        combo_count = 0

        try:
            for combo in itertools.product(*values):
                if combo_count >= max_combos:
                    break
                combo_count += 1
                params = dict(zip(keys, combo))
                strategy.parameters = params
                bt = self.backtest.run_python_backtest(strategy, symbol)
                metrics = bt.metrics or {}
                entry = {"parameters": params, "metrics": metrics}
                results.append(entry)
                if best is None or metrics.get("net_pnl", 0) > best["metrics"].get("net_pnl", 0):
                    best = entry

            run.status = "completed"
            run.results = {"all": results, "count": len(results)}
            run.best_parameters = best["parameters"] if best else None
            run.best_metrics = best["metrics"] if best else None
            run.completed_at = datetime.utcnow()
        except Exception as exc:
            run.status = "failed"
            run.results = {"error": str(exc)}
            logger.error("grid_search_failed", error=str(exc))

        self.session.commit()
        return run

    def run_genetic_search(
        self,
        strategy: Strategy,
        symbol: str,
        parameter_space: dict[str, tuple[float, float]],
        generations: int = 10,
        population: int = 20,
    ) -> OptimizationRun:
        """Simple GA over continuous parameter ranges (MVP)."""
        import numpy as np

        run = OptimizationRun(
            strategy_id=strategy.id,
            method="genetic",
            status="running",
            parameter_space=parameter_space,
        )
        self.session.add(run)
        self.session.commit()

        keys = list(parameter_space.keys())
        bounds = np.array([parameter_space[k] for k in keys])
        rng = np.random.default_rng(42)

        from src.services.resource_profile import get_resource_profile

        prof = get_resource_profile()
        if prof.low_ram:
            generations = min(generations, 5)
            population = min(population, 8)

        def random_individual() -> np.ndarray:
            return rng.uniform(bounds[:, 0], bounds[:, 1])

        def fitness(ind: np.ndarray) -> float:
            params = {k: float(v) for k, v in zip(keys, ind)}
            strategy.parameters = params
            bt = self.backtest.run_python_backtest(strategy, symbol, seed=int(ind.sum() * 100) % 10000)
            return float((bt.metrics or {}).get("net_pnl", 0))

        try:
            pop = [random_individual() for _ in range(population)]
            history: list[dict[str, Any]] = []
            best_ind = pop[0]
            best_fit = fitness(best_ind)

            for gen in range(generations):
                scores = [fitness(ind) for ind in pop]
                idx = int(np.argmax(scores))
                if scores[idx] > best_fit:
                    best_fit = scores[idx]
                    best_ind = pop[idx]

                history.append({"generation": gen, "best_pnl": best_fit})

                # Selection + mutation
                sorted_pop = [pop[i] for i in np.argsort(scores)[-population // 2 :]]
                new_pop = sorted_pop.copy()
                while len(new_pop) < population:
                    p1, p2 = rng.choice(sorted_pop, 2, replace=False)
                    child = (p1 + p2) / 2 + rng.normal(0, 0.1, size=len(keys))
                    child = np.clip(child, bounds[:, 0], bounds[:, 1])
                    new_pop.append(child)
                pop = new_pop

            best_params = {k: float(v) for k, v in zip(keys, best_ind)}
            strategy.parameters = best_params
            bt = self.backtest.run_python_backtest(strategy, symbol)
            run.status = "completed"
            run.best_parameters = best_params
            run.best_metrics = bt.metrics
            run.results = {"history": history, "generations": generations}
            run.completed_at = datetime.utcnow()
        except Exception as exc:
            run.status = "failed"
            run.results = {"error": str(exc)}

        self.session.commit()
        return run
