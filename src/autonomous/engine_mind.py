"""Engine Mind — real-time autonomous state, sources, cycle breakdown (10.0)."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from src.config import get_settings
from src.services.resource_profile import detect_compute_device, get_resource_profile


@dataclass(slots=True)
class CycleRecord:
    phase: str
    ts: float
    duration_ms: float | None
    symbol: str | None
    meta: dict[str, Any]


@dataclass
class EngineMind:
    """Thread-safe motor state — bounded deque keeps RAM flat."""

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _cycles: deque[CycleRecord] = field(default_factory=lambda: deque(maxlen=120))
    _phase: str = "idle"
    _last_error: str | None = None
    _started_at: float = field(default_factory=time.time)

    def record_cycle(
        self,
        phase: str,
        *,
        symbol: str | None = None,
        duration_ms: float | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            self._phase = phase
            self._cycles.append(
                CycleRecord(
                    phase=phase,
                    ts=time.time(),
                    duration_ms=duration_ms,
                    symbol=symbol,
                    meta=meta or {},
                )
            )

    def record_error(self, message: str) -> None:
        with self._lock:
            self._last_error = message[:500]
            self._phase = "error"

    def snapshot(self) -> dict[str, Any]:
        settings = get_settings()
        prof = get_resource_profile()
        compute = detect_compute_device()
        with self._lock:
            recent = list(self._cycles)[-20:]
            breakdown: dict[str, int] = {}
            for c in recent:
                breakdown[c.phase] = breakdown.get(c.phase, 0) + 1
            from src.services.self_healing import all_breakers_snapshot

            return {
                "enabled": settings.engine_mind_enabled,
                "phase": self._phase,
                "uptime_sec": round(time.time() - self._started_at, 1),
                "last_error": self._last_error,
                "sources": {
                    "replay_training": settings.replay_training_enabled,
                    "strategy_store": settings.strategy_store_enabled,
                    "wfo": settings.walk_forward_auto_promote,
                    "ollama": settings.ollama_runtime_enabled,
                    "profit_bridge": settings.profit_bridge_enabled,
                },
                "resources": {
                    "ram_budget_mb": prof.effective_ram_budget_mb,
                    "ram_fraction": settings.resource_ram_fraction,
                    "gpu_fraction": settings.resource_gpu_fraction,
                    "replay_workers": settings.effective_replay_workers,
                    "optimization_workers": prof.max_optimization_workers,
                    "compute": compute,
                },
                "cycle_breakdown": breakdown,
                "circuit_breakers": all_breakers_snapshot(),
                "recent_cycles": [
                    {
                        "phase": c.phase,
                        "symbol": c.symbol,
                        "duration_ms": c.duration_ms,
                        "meta": c.meta,
                        "ago_sec": round(time.time() - c.ts, 1),
                    }
                    for c in reversed(recent)
                ],
            }


_mind: EngineMind | None = None
_mind_lock = threading.Lock()


def get_engine_mind() -> EngineMind:
    global _mind
    with _mind_lock:
        if _mind is None:
            _mind = EngineMind()
        return _mind
