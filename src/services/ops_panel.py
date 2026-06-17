"""Ops panel metrics — RAM, motor cycle, background test status (7.0)."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT, get_settings

TEST_STATUS_PATH = PROJECT_ROOT / "data" / ".dev" / "test_status.json"

_motor_cycle_ms: float | None = None
_motor_cycle_history: deque[float] = deque(maxlen=40)


def set_motor_cycle_ms(ms: float) -> None:
    global _motor_cycle_ms
    _motor_cycle_ms = ms
    _motor_cycle_history.append(ms)


def get_motor_cycle_ms() -> float | None:
    return _motor_cycle_ms


def read_test_status() -> dict[str, Any]:
    if not TEST_STATUS_PATH.exists():
        return {
            "state": "yellow",
            "message": "No test run yet",
            "count": 0,
            "duration_sec": 0,
            "timestamp": None,
        }
    try:
        data = json.loads(TEST_STATUS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("state", "yellow")
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"state": "red", "message": "Invalid test_status.json", "count": 0}


def _read_ram_snapshot() -> dict[str, Any]:
    path = PROJECT_ROOT / "data" / ".dev" / "ram_snapshot.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _stack_rss_mb(proc: Any) -> float | None:
    try:
        import psutil

        total = proc.memory_info().rss
        for child in proc.children(recursive=True):
            try:
                total += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return round(total / (1024 * 1024), 1)
    except Exception:
        return None


def get_process_rss_mb() -> dict[str, Any]:
    """Process RSS breakdown — psutil when available, else stub."""
    snapshot = _read_ram_snapshot()
    try:
        import psutil

        proc = psutil.Process()
        mem = proc.memory_info()
        total_mb = round(mem.rss / (1024 * 1024), 1)
        stack_mb = _stack_rss_mb(proc)
        children: list[dict[str, Any]] = []
        for child in proc.children(recursive=True):
            try:
                cm = child.memory_info()
                children.append(
                    {
                        "pid": child.pid,
                        "name": child.name(),
                        "rss_mb": round(cm.rss / (1024 * 1024), 1),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        rss_for_budget = float(snapshot.get("stack_rss_mb") or stack_mb or total_mb)
        return {
            "rss_mb": rss_for_budget,
            "process_rss_mb": total_mb,
            "stack_rss_mb": stack_mb,
            "available": True,
            "children": children[:8],
            "stub": False,
            "snapshot_at": snapshot.get("timestamp"),
        }
    except ImportError:
        if snapshot.get("stack_rss_mb") is not None:
            return {
                "rss_mb": float(snapshot["stack_rss_mb"]),
                "available": True,
                "stub": True,
                "children": [],
                "snapshot_at": snapshot.get("timestamp"),
            }
        return {"rss_mb": 0.0, "available": False, "stub": True, "children": []}


def motor_cycle_p95_ms() -> float | None:
    if not _motor_cycle_history:
        return None
    ordered = sorted(_motor_cycle_history)
    idx = max(0, int(len(ordered) * 0.95) - 1)
    return round(ordered[idx], 0)


def build_ops_panel() -> dict[str, Any]:
    from src.services.resource_profile import get_resource_profile, profile_snapshot
    from src.services.trading_orchestrator import orchestrator_status

    settings = get_settings()
    res_profile = get_resource_profile(settings)
    test_status = read_test_status()
    memory = get_process_rss_mb()
    motor_ms = get_motor_cycle_ms()
    orch = orchestrator_status()
    rss = float(memory.get("rss_mb") or 0)
    budget = res_profile.effective_ram_budget_mb
    return {
        "motor_cycle_ms": round(motor_ms, 0) if motor_ms is not None else None,
        "motor_cycle_p95_ms": motor_cycle_p95_ms(),
        "motor_active": orch.get("active"),
        "motor_last_run": orch.get("last_run"),
        "memory": memory,
        "test_status": test_status,
        "ram_budget_mb": budget,
        "ram_over_budget": bool(memory.get("available") and rss > budget),
        "resource_profile": profile_snapshot(settings),
    }
