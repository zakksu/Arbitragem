"""Domain models for the autonomous engine (Pydantic-friendly dicts)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RankingRow:
    """One row in Strategy Lab rankings table."""

    id: int
    symbol: str
    strategy_id: int | None
    strategy_name: str
    sector: str
    structure_type: str
    idea_score: float
    wf_score: float
    profit_factor: float
    max_drawdown_pct: float
    win_rate: float
    status: str
    last_optimized_at: datetime | None
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "sector": self.sector,
            "structure_type": self.structure_type,
            "idea_score": self.idea_score,
            "wf_score": self.wf_score,
            "profit_factor": self.profit_factor,
            "max_drawdown_pct": self.max_drawdown_pct,
            "win_rate": self.win_rate,
            "status": self.status,
            "last_optimized_at": (
                self.last_optimized_at.isoformat() if self.last_optimized_at else None
            ),
            "parameters": self.parameters,
        }


@dataclass
class RankingDetail(RankingRow):
    """Detailed view — equity curve, folds, commentary."""

    fold_results: list[dict[str, Any]] = field(default_factory=list)
    parameter_history: list[dict[str, Any]] = field(default_factory=list)
    equity_curve: list[dict[str, Any]] = field(default_factory=list)
    ollama_commentary: str | None = None
    optimization_run_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "fold_results": self.fold_results,
                "parameter_history": self.parameter_history,
                "equity_curve": self.equity_curve,
                "ollama_commentary": self.ollama_commentary,
                "optimization_run_id": self.optimization_run_id,
            }
        )
        return base


@dataclass
class DailyRoutineResult:
    """Outcome of one autonomous daily tick."""

    scan_count: int = 0
    ideas_generated: int = 0
    rankings_synced: int = 0
    wfo_runs: int = 0
    risk_blocked: bool = False
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scan_count": self.scan_count,
            "ideas_generated": self.ideas_generated,
            "rankings_synced": self.rankings_synced,
            "wfo_runs": self.wfo_runs,
            "risk_blocked": self.risk_blocked,
            "errors": self.errors,
        }
