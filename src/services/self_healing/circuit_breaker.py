"""Circuit breakers — pause replay/motor on repeated failures (10.0 self-healing)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CircuitBreaker:
    """Simple failure-count breaker with half-open after cooldown."""

    name: str
    failure_threshold: int = 5
    reset_sec: float = 300.0
    _failures: int = 0
    _opened_at: float | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def is_open(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return False
            if time.monotonic() - self._opened_at >= self.reset_sec:
                self._opened_at = None
                self._failures = 0
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._opened_at = time.monotonic()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            open_now = self._opened_at is not None and (
                time.monotonic() - self._opened_at < self.reset_sec
            )
            return {
                "name": self.name,
                "open": open_now,
                "failures": self._failures,
                "threshold": self.failure_threshold,
                "reset_sec": self.reset_sec,
            }


_registry: dict[str, CircuitBreaker] = {}
_reg_lock = threading.Lock()


def get_breaker(name: str, *, failure_threshold: int = 5, reset_sec: float = 300.0) -> CircuitBreaker:
    with _reg_lock:
        if name not in _registry:
            _registry[name] = CircuitBreaker(name, failure_threshold, reset_sec)
        return _registry[name]


def all_breakers_snapshot() -> list[dict[str, Any]]:
    with _reg_lock:
        return [b.snapshot() for b in _registry.values()]
