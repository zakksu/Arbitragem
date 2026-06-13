"""Hybrid backtesting — ProfitChart primary, Python supplement.

RECOMMENDATION (see README):
  - Use ProfitChart Tick-a-Tick for NTSL strategy validation (fast, B3-realistic)
  - Use Python layer for grid search, walk-forward, and ML-heavy optimization
  - Compare both engines via compare_engines()
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from src.integrations.profit_bridge import get_profit_client
from src.logging_config import get_logger
from src.models import BacktestRun, Strategy

logger = get_logger(__name__)


@dataclass
class BacktestMetrics:
    total_trades: int
    net_pnl: float
    win_rate: float
    max_drawdown: float
    sharpe: float
    profit_factor: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_trades": self.total_trades,
            "net_pnl": self.net_pnl,
            "win_rate": self.win_rate,
            "max_drawdown": self.max_drawdown,
            "sharpe": self.sharpe,
            "profit_factor": self.profit_factor,
        }


class BacktestService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.profit = get_profit_client()

    def run_profit_backtest(
        self,
        strategy: Strategy,
        symbol: str,
        profit_csv_path: Path | None = None,
    ) -> BacktestRun:
        """Record backtest from ProfitChart CSV export."""
        metrics: dict[str, Any]
        if profit_csv_path and profit_csv_path.exists():
            metrics = self.profit.import_backtest_results(profit_csv_path)
        else:
            metrics = {
                "source": "profit_chart",
                "note": "Export CSV from Profit Backtest and pass path",
                "total_trades": 0,
                "net_pnl": 0.0,
                "win_rate": 0.0,
                "max_drawdown": 0.0,
            }

        run = BacktestRun(
            strategy_id=strategy.id,
            engine="profit",
            symbol=symbol,
            parameters=strategy.parameters,
            metrics=metrics,
            profit_export_path=str(profit_csv_path) if profit_csv_path else None,
            notes="ProfitChart Tick-a-Tick backtest import",
        )
        self.session.add(run)
        self.session.commit()
        return run

    def run_python_backtest(
        self,
        strategy: Strategy,
        symbol: str,
        bars: int = 500,
        seed: int = 42,
    ) -> BacktestRun:
        """Lightweight vectorized mock backtest for parameter sweeps.

        Replace `_simulate_returns` with real tick/bar data from ProfitDLL export
        or a historical data provider when ready.
        """
        params = strategy.parameters or {}
        stop_ticks = float(params.get("stop_ticks", 5))
        target_ticks = float(params.get("target_ticks", 8))

        returns = self._simulate_returns(bars, seed, stop_ticks, target_ticks)
        metrics = self._compute_metrics(returns)

        run = BacktestRun(
            strategy_id=strategy.id,
            engine="python",
            symbol=symbol,
            parameters=strategy.parameters,
            metrics=metrics.to_dict(),
            notes="Python supplement backtest (replace with real data)",
        )
        self.session.add(run)
        self.session.commit()
        return run

    def compare_engines(
        self,
        strategy: Strategy,
        symbol: str,
        profit_csv_path: Path | None = None,
    ) -> dict[str, Any]:
        profit_run = self.run_profit_backtest(strategy, symbol, profit_csv_path)
        python_run = self.run_python_backtest(strategy, symbol)
        return {
            "profit": profit_run.metrics,
            "python": python_run.metrics,
            "delta_pnl": (python_run.metrics or {}).get("net_pnl", 0)
            - (profit_run.metrics or {}).get("net_pnl", 0),
            "recommendation": (
                "Trust ProfitChart for NTSL execution realism; "
                "use Python for parameter search only until data is aligned."
            ),
        }

    @staticmethod
    def _simulate_returns(
        bars: int, seed: int, stop_ticks: float, target_ticks: float
    ) -> np.ndarray:
        rng = np.random.default_rng(seed)
        edge = (target_ticks - stop_ticks) / (target_ticks + stop_ticks)
        return rng.normal(loc=edge * 0.01, scale=0.02, size=bars)

    @staticmethod
    def _compute_metrics(returns: np.ndarray) -> BacktestMetrics:
        equity = np.cumsum(returns)
        peak = np.maximum.accumulate(equity)
        drawdown = peak - equity
        wins = returns[returns > 0]
        losses = returns[returns < 0]
        win_rate = len(wins) / len(returns) if len(returns) else 0.0
        gross_profit = wins.sum() if len(wins) else 0.0
        gross_loss = abs(losses.sum()) if len(losses) else 1e-9
        sharpe = (returns.mean() / (returns.std() + 1e-9)) * np.sqrt(252)

        return BacktestMetrics(
            total_trades=int(len(returns)),
            net_pnl=float(returns.sum()),
            win_rate=float(win_rate),
            max_drawdown=float(drawdown.max() if len(drawdown) else 0.0),
            sharpe=float(sharpe),
            profit_factor=float(gross_profit / gross_loss),
        )
