"""Autonomous scanner — thin async wrapper over PatternScanner."""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.orm import Session

from src.services.scanner import PatternScanner
from src.services.trade_ideas import TradeIdeaService


class AutonomousScanner:
    def __init__(self, session: Session) -> None:
        self.session = session

    def run_scan_sync(self) -> tuple[int, int]:
        from src.services.resource_profile import get_resource_profile

        limit = get_resource_profile().autonomous_ideas_limit
        results = PatternScanner(self.session).run_daily_scan()
        ideas = TradeIdeaService(self.session).generate_from_latest_scan(limit=limit)
        return len(results), len(ideas)

    async def run_scan(self) -> dict[str, Any]:
        count, ideas_n = await asyncio.to_thread(self.run_scan_sync)
        return {"scan_count": count, "ideas_generated": ideas_n}
