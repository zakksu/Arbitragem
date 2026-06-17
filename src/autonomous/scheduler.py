"""Autonomous scheduler — registers background jobs (WFO + rankings sync)."""

from __future__ import annotations

import asyncio
from typing import Any

from src.config import get_settings
from src.logging_config import get_logger
from src.models import get_session_factory

logger = get_logger(__name__)


def run_rankings_sync_sync() -> dict[str, Any]:
    """Sync Strategy Lab rankings from optimization runs (scheduler-safe)."""
    from src.autonomous.backtest_rankings import BacktestRankingsService

    session = get_session_factory()()
    try:
        n = BacktestRankingsService(session).sync_from_optimization_runs()
        logger.info("rankings_sync_complete", count=n)
        return {"synced": n}
    finally:
        session.close()


async def run_rankings_sync() -> dict[str, Any]:
    return await asyncio.to_thread(run_rankings_sync_sync)


def register_autonomous_jobs(scheduler) -> None:
    """Hook into APScheduler after core jobs."""
    settings = get_settings()
    if not getattr(settings, "autonomous_rankings_sync", True):
        return
    interval = max(1, getattr(settings, "rankings_sync_interval_hours", 6))
    scheduler.add_job(
        run_rankings_sync_sync,
        "interval",
        hours=interval,
        id="rankings_sync",
        replace_existing=True,
    )
    logger.info("autonomous_scheduler_registered", rankings_interval_hours=interval)
