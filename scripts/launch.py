#!/usr/bin/env python3
"""One-shot launcher — setup, start stack, open sleeves, print URLs (local only)."""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _py() -> str:
    venv = ROOT / ".venv" / "Scripts" / "python.exe"
    if venv.is_file():
        return str(venv)
    return sys.executable


def _post_json(url: str, payload: dict) -> dict | None:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def main() -> int:
    py = _py()
    print("[launch] Arbitragem — local trader desk launcher\n")

    if not (ROOT / ".venv").is_dir():
        print("[launch] First run — setup (venv, deps, DB)...")
        subprocess.run([py, str(ROOT / "scripts" / "dev.py"), "setup"], cwd=ROOT, check=False)

    print("[launch] Starting API + dashboard + profit bridge...")
    r = subprocess.run(
        [py, str(ROOT / "scripts" / "dev.py"), "start", "--wait", "--json"],
        cwd=ROOT,
    )
    if r.returncode != 0:
        print("[launch] Start failed — see logs/api.log", file=sys.stderr)
        return r.returncode

    print("[launch] Opening trading sleeves...")
    _post_json("http://127.0.0.1:8000/api/v1/risk/sleeves", {"all_open": True})

    print("\n[launch] READY (local — no tunnel/hosting)\n")
    print("  Board:     http://127.0.0.1:8000/board")
    print("  Dashboard: http://127.0.0.1:8501")
    print("  API docs:  http://127.0.0.1:8000/docs")
    print("  Login:     admin / admin (dashboard + public board only)")
    print("\n  Stop:      python scripts/dev.py stop")
    print("  Status:    python scripts/status_tick.py\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
