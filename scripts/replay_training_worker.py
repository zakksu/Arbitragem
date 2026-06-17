#!/usr/bin/env python3
"""Background replay training worker — non-blocking PETR4 sandboxes (10.0)."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "data" / ".dev" / "replay_training_status.json"
DEFAULT_INTERVAL_MIN = 30


def _py() -> str:
    venv = ROOT / ".venv" / "Scripts" / "python.exe"
    return str(venv) if venv.is_file() else sys.executable


def _write_status(payload: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_once() -> dict:
    sys.path.insert(0, str(ROOT))
    from src.config import get_settings
    from src.models import get_session_factory, init_db
    from src.services.replay_engine import run_training_cycle

    get_settings.cache_clear()
    settings = get_settings()
    if not settings.replay_training_enabled:
        return {"state": "disabled", "message": "REPLAY_TRAINING_ENABLED=false"}

    init_db()
    session = get_session_factory()()
    started = time.time()
    try:
        result = run_training_cycle(session)
        elapsed = round(time.time() - started, 2)
        payload = {
            "state": "green",
            "message": result.get("message", "ok"),
            "runs": result.get("runs", []),
            "duration_sec": elapsed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _write_status(payload)
        return payload
    except Exception as exc:
        payload = {
            "state": "red",
            "message": str(exc)[:300],
            "duration_sec": round(time.time() - started, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _write_status(payload)
        return payload
    finally:
        session.close()


def main() -> int:
    once = "--once" in sys.argv
    interval = int(os.getenv("REPLAY_TRAINING_INTERVAL_MIN", str(DEFAULT_INTERVAL_MIN)))
    interval = max(5, interval)

    if once:
        out = run_once()
        print(json.dumps(out, indent=2))
        return 0 if out.get("state") in ("green", "disabled") else 1

    print(f"[replay_training_worker] every {interval}m -> {STATUS_PATH}", flush=True)
    while True:
        out = run_once()
        print(f"[replay_training_worker] {out.get('state')}: {out.get('message', '')}", flush=True)
        time.sleep(interval * 60)


if __name__ == "__main__":
    raise SystemExit(main())
