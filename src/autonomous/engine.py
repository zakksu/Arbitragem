"""Autonomous engine — daily routine orchestrating scan, WFO, rankings, risk."""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

from sqlalchemy.orm import Session

from src.autonomous.backtest_rankings import BacktestRankingsService
from src.autonomous.journal_analyzer import JournalAnalyzer
from src.autonomous.models import DailyRoutineResult
from src.autonomous.optimizer import AutonomousOptimizer
from src.autonomous.risk_guardian import RiskGuardian
from src.autonomous.scanner import AutonomousScanner
from src.config import get_settings
from src.logging_config import get_logger
from src.models import Strategy
from src.services.strategy_manager import StrategyService
from src.services.walk_forward_promotion import run_walk_forward_promotion

logger = get_logger(__name__)


class AutonomousEngine:
    """Top-level motor for background autonomous jobs."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.risk = RiskGuardian(session)
        self.scanner = AutonomousScanner(session)
        self.optimizer = AutonomousOptimizer(session)
        self.rankings = BacktestRankingsService(session)
        self.journal = JournalAnalyzer(session)

    def run_daily_routine_sync(self) -> DailyRoutineResult:
        result = DailyRoutineResult()
        ok, reason = self.risk.can_run_autonomous()
        if not ok:
            result.risk_blocked = True
            result.errors.append(reason or "risk_blocked")
            return result

        settings = get_settings()
        try:
            scan = self.scanner.run_scan_sync()
            result.scan_count, result.ideas_generated = scan
        except Exception as exc:
            logger.exception("autonomous_scan_failed")
            result.errors.append(f"scan:{exc}")

        if settings.walk_forward_auto_promote:
            try:
                promo = run_walk_forward_promotion(
                    self.session, folds=settings.walk_forward_promote_folds
                )
                result.wfo_runs = int(promo.get("runs_completed") or 0)
            except Exception as exc:
                result.errors.append(f"wfo:{exc}")

        try:
            result.rankings_synced = self.rankings.sync_from_optimization_runs()
        except Exception as exc:
            result.errors.append(f"rankings:{exc}")

        try:
            self.journal.sync_sources()
        except Exception as exc:
            result.errors.append(f"journal:{exc}")

        self.session.commit()
        logger.info("autonomous_daily_routine", **result.to_dict())
        return result

    async def run_daily_routine(self) -> dict[str, Any]:
        return (await asyncio.to_thread(self.run_daily_routine_sync)).to_dict()

    async def run_wfo_for_active_strategies(self, *, folds: int = 3) -> list[dict[str, Any]]:
        from src.services.resource_profile import get_resource_profile

        strat_limit = get_resource_profile().autonomous_strategy_limit
        strategies = (
            self.session.query(Strategy).filter(Strategy.status == "active").limit(strat_limit).all()
        )
        if not strategies:
            strategies = [StrategyService(self.session).get_or_create_sample()]
        return await self.optimizer.run_wfo_batch(strategies, folds=folds)


@lru_cache
def get_autonomous_engine() -> type[AutonomousEngine]:
    return AutonomousEngine
