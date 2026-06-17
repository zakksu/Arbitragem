"""Replay runner — delegates to replay training engine (10.0)."""

from __future__ import annotations

import asyncio
from typing import Any


class ReplayRunner:
    """Runs replay training cycles for autonomous validation."""

    async def run(self, symbol: str, *, strategy: str = "scalp_long", speed: float = 10.0) -> dict[str, Any]:
        from src.services.replay_engine import start_replay

        return await asyncio.to_thread(
            start_replay,
            strategy=strategy,
            symbol=symbol.strip().upper(),
            speed=speed,
            mode="training",
        )
