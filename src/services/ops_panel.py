"""Ops panel metrics — RAM, motor cycle, background test status (7.0)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT

TEST_STATUS_PATH = PROJECT_ROOT / "data" / ".dev" / "test_status.json"

_motor_cycle_ms: float | None = None


def set_motor_cycle_ms(ms: float) -> None:
    global _motor_cycle_ms
    _motor_cycle_ms = ms


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


def get_process_rss_mb() -> dict[str, Any]:
    """Process RSS breakdown — psutil when available, else stub."""
    try:
        import psutil

        proc = psutil.Process()
        mem = proc.memory_info()
        total_mb = round(mem.rss / (1024 * 1024), 1)
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
        return {
            "rss_mb": total_mb,
            "available": True,
            "children": children[:8],
            "stub": False,
        }
    except ImportError:
        return {"rss_mb": 0.0, "available": False, "stub": True, "children": []}


def build_ops_panel() -> dict[str, Any]:
    from src.services.trading_orchestrator import orchestrator_status

    test_status = read_test_status()
    memory = get_process_rss_mb()
    motor_ms = get_motor_cycle_ms()
    orch = orchestrator_status()
    return {
        "motor_cycle_ms": round(motor_ms, 0) if motor_ms is not None else None,
        "motor_active": orch.get("active"),
        "motor_last_run": orch.get("last_run"),
        "memory": memory,
        "test_status": test_status,
        "ram_budget_mb": 1200,
    }
