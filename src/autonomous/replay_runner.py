"""Replay runner — sandbox backtests for autonomous validation."""

from __future__ import annotations

import asyncio
from typing import Any


class ReplayRunner:
    """Delegates to replay lab service (stub-friendly)."""

    async def run(self, symbol: str, *, strategy: str = "scalp_long", speed: float = 10.0) -> dict[str, Any]:
        from src.services.replay_lab import start_replay

        return await asyncio.to_thread(
            start_replay,
            strategy=strategy,
            symbol=symbol.strip().upper(),
            speed=speed,
            mode="sandbox",
        )
