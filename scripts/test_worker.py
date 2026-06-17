#!/usr/bin/env python3
"""Background pytest worker — writes data/.dev/test_status.json (Release 7.0)."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_DIR = ROOT / "data" / ".dev"
STATUS_PATH = STATUS_DIR / "test_status.json"
DEFAULT_TESTS = [
    "tests/test_golden_path_petr4.py",
    "tests/test_golden_path_mode.py",
    "tests/test_symbol_factory.py",
]
DEFAULT_INTERVAL = 300


def _python() -> str:
    venv = ROOT / ".venv"
    if sys.platform == "win32":
        candidate = venv / "Scripts" / "python.exe"
    else:
        candidate = venv / "bin" / "python"
    return str(candidate) if candidate.exists() else sys.executable


def _write_status(payload: dict) -> None:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_pytest(test_paths: list[str] | None = None) -> dict:
    paths = test_paths or DEFAULT_TESTS
    existing = [p for p in paths if (ROOT / p).exists()]
    if not existing:
        existing = ["tests/"]

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env.setdefault("APP_ENV", "test")
    env.setdefault("PROFIT_BRIDGE_ENABLED", "false")
    env.setdefault("ENABLE_SCHEDULER", "false")

    cmd = [
        _python(),
        "-m",
        "pytest",
        *existing,
        "-q",
        "--tb=no",
    ]
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    duration = round(time.perf_counter() - started, 2)

    combined = (proc.stdout or "") + (proc.stderr or "")
    passed = len(re.findall(r" passed", combined))
    failed = len(re.findall(r" failed", combined))
    errors = len(re.findall(r" error", combined))

    if proc.returncode == 0:
        state = "green"
        message = f"{passed} passed"
    elif proc.returncode == 5:
        state = "yellow"
        message = "No tests collected"
    else:
        state = "red"
        message = f"{failed} failed, {errors} errors"

    payload = {
        "state": state,
        "message": message,
        "count": passed,
        "failed": failed,
        "duration_sec": duration,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "exit_code": proc.returncode,
        "tests": existing,
    }
    _write_status(payload)
    return payload


def cmd_once(args: argparse.Namespace) -> int:
    paths = args.tests.split(",") if args.tests else None
    result = run_pytest(paths)
    print(json.dumps(result, indent=2))
    return 0 if result["state"] == "green" else 1


def cmd_loop(args: argparse.Namespace) -> int:
    interval = max(30, args.interval)
    paths = args.tests.split(",") if args.tests else None
    print(f"[test_worker] loop every {interval}s — Ctrl+C to stop")
    while True:
        result = run_pytest(paths)
        print(f"[test_worker] {result['state']} — {result['message']} ({result['duration_sec']}s)")
        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Background pytest worker")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Loop interval seconds")
    parser.add_argument("--tests", help="Comma-separated test paths")
    args = parser.parse_args()
    if args.once:
        return cmd_once(args)
    return cmd_loop(args)


if __name__ == "__main__":
    raise SystemExit(main())
