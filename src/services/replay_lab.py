"""Replay lab sandbox stub — ProfitChart replay job (4.0-beta)."""

from __future__ import annotations

import uuid
from datetime import datetime

_REPLAY_RUNS: dict[str, dict] = {}


def start_replay(
    *,
    strategy: str,
    symbol: str,
    speed: float = 10.0,
    mode: str = "sandbox",
) -> dict:
    speed = max(1.0, min(20.0, float(speed)))
    job_id = str(uuid.uuid4())[:8]
    run = {
        "job_id": job_id,
        "strategy": strategy,
        "symbol": symbol.upper(),
        "speed": speed,
        "mode": mode,
        "status": "queued",
        "progress_pct": 0,
        "message": "Open ProfitChart replay manually if DLL auto-start unavailable.",
        "started_at": datetime.utcnow().isoformat() + "Z",
        "fills": [],
    }
    _REPLAY_RUNS[job_id] = run
    return run


def get_replay(job_id: str) -> dict | None:
    return _REPLAY_RUNS.get(job_id)
