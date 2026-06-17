#!/usr/bin/env python3
"""Compact status for agent loop / Filipe — motor, desk, health."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime


def _get(url: str, timeout: float = 8.0) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


def _symbol_factory_summary() -> dict | None:
    try:
        sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
        from src.models import get_session_factory, init_db
        from src.services.symbol_factory import factory_status

        init_db()
        session = get_session_factory()()
        try:
            data = factory_status(session)
            return {
                "locked": data.get("locked"),
                "lock_reasons": data.get("lock_reasons"),
                "shadow_count": len(data.get("shadow_symbols") or []),
                "motor_count": len(data.get("motor_symbols") or []),
            }
        finally:
            session.close()
    except Exception:
        return None


def _stack_rss_mb() -> float | None:
    try:
        import psutil

        proc = psutil.Process()
        total = proc.memory_info().rss
        for child in proc.children(recursive=True):
            try:
                total += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return round(total / (1024 * 1024), 1)
    except ImportError:
        return None


def _golden_path_summary() -> dict | None:
    try:
        sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
        from src.models import get_session_factory, init_db
        from src.services.golden_path import golden_path_summary

        init_db()
        session = get_session_factory()()
        try:
            return golden_path_summary(session)
        finally:
            session.close()
    except Exception:
        return None


def _test_status() -> dict:
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "data" / ".dev" / "test_status.json"
    if not path.exists():
        return {"state": "yellow", "message": "No test run yet"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"state": "red", "message": "Invalid test_status.json"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Arbitragem status tick")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    args = parser.parse_args()

    now = datetime.now().strftime("%H:%M:%S")
    health = _get("http://127.0.0.1:8000/api/v1/health/live")
    orch = _get("http://127.0.0.1:8000/api/v1/orchestrator/status")
    sleeves = _get("http://127.0.0.1:8000/api/v1/risk/sleeves")
    test_status = _test_status()
    golden_path = _golden_path_summary()
    symbol_factory = _symbol_factory_summary()
    ram_mb = _stack_rss_mb()
    try:
        from src.config import get_settings
        from src.services.resource_profile import profile_snapshot

        resource_profile = profile_snapshot(get_settings())
    except Exception:
        resource_profile = None

    if args.json:
        payload = {
            "timestamp": now,
            "api": {"ok": health is not None, "health": health},
            "motor": orch,
            "sleeves": sleeves,
            "test_status": test_status,
            "golden_path": golden_path,
            "symbol_factory": symbol_factory,
            "ram_mb": ram_mb,
            "resource_profile": resource_profile,
        }
        print(json.dumps(payload, indent=2, default=str))
        return 0 if health else 1

    lines = [f"[status {now}]"]
    if not health:
        lines.append("API OFFLINE — run: python scripts/launch.py")
        print("\n".join(lines))
        return 1

    lines.append("API: OK")
    if orch:
        lines.append(
            f"Motor: {'ACTIVE' if orch.get('active') else 'idle'} "
            f"last_run={orch.get('last_run') or '—'} "
            f"paper={orch.get('paper_auto')}"
        )
        last = orch.get("last_autonomy") or {}
        actions = last.get("actions") or []
        if actions:
            lines.append(f"Last actions: {len(actions)}")
    if sleeves:
        s = sleeves.get("sleeves") or {}
        lines.append(f"Sleeves: cash={s.get('cash')} opt={s.get('options')} pair={s.get('pairs')}")
    if test_status:
        lines.append(f"Tests: {test_status.get('state', '—').upper()} — {test_status.get('message', '')}")
    if golden_path:
        lines.append(
            f"Golden path: {golden_path.get('items_ok', 0)}/{golden_path.get('items_total', 7)} "
            f"sessions={golden_path.get('sessions_green_count', 0)}"
        )
    if symbol_factory:
        lock = "LOCKED" if symbol_factory.get("locked") else "open"
        lines.append(
            f"Symbol factory: {lock} shadow={symbol_factory.get('shadow_count', 0)}"
        )
    if ram_mb is not None:
        lines.append(f"RAM: {ram_mb} MB")

    lines.append("Board: http://127.0.0.1:8000/board")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
