#!/usr/bin/env python3
"""Record today's golden path session when checklist is all green (Release 7.0 dev tooling)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSIONS_PATH = ROOT / "data" / "golden_path_sessions.json"


def _load_sessions() -> dict:
    if not SESSIONS_PATH.exists():
        return {"green_dates": [], "green_count": 0}
    try:
        data = json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("green_dates", [])
            data["green_count"] = len(data["green_dates"])
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"green_dates": [], "green_count": 0}


def _save_sessions(data: dict) -> None:
    SESSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    dates = sorted(set(data.get("green_dates") or []))
    payload = {
        "green_dates": dates,
        "green_count": len(dates),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    SESSIONS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def evaluate() -> dict:
    sys.path.insert(0, str(ROOT))
    from src.models import get_session_factory, init_db
    from src.services.golden_path import evaluate_golden_path

    init_db()
    session = get_session_factory()()
    try:
        return evaluate_golden_path(session)
    finally:
        session.close()


def record_today() -> dict:
    data = evaluate()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sessions = _load_sessions()
    dates = list(sessions.get("green_dates") or [])

    if not data.get("all_green"):
        return {
            "recorded": False,
            "reason": "checklist_not_all_green",
            "today": today,
            "sessions_green_count": data.get("sessions_green_count", 0),
            "items_ok": sum(1 for it in data.get("items", []) if it.get("ok")),
        }

    if today not in dates:
        dates.append(today)
        sessions["green_dates"] = dates
        _save_sessions(sessions)

    return {
        "recorded": today in dates,
        "today": today,
        "sessions_green_count": len(dates),
        "all_green": True,
    }


def dev_fill_sessions(count: int) -> dict:
    """Dev-only: add N consecutive calendar days ending today (for factory unlock testing)."""
    sessions = _load_sessions()
    dates = set(sessions.get("green_dates") or [])
    today = datetime.now(timezone.utc).date()
    for offset in range(count - 1, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        dates.add(day)
    sessions["green_dates"] = sorted(dates)
    _save_sessions(sessions)
    return {"dev_fill": True, "sessions_green_count": len(dates), "green_dates": sorted(dates)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Record golden path green session for today")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate only; do not write")
    parser.add_argument(
        "--dev-fill-sessions",
        type=int,
        metavar="N",
        help="DEV ONLY: write N consecutive green session dates (factory unlock testing)",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.dev_fill_sessions:
        result = dev_fill_sessions(max(1, args.dev_fill_sessions))
    elif args.dry_run:
        data = evaluate()
        result = {
            "dry_run": True,
            "all_green": data.get("all_green"),
            "sessions_green_count": data.get("sessions_green_count"),
            "would_record_today": bool(data.get("all_green")),
        }
    else:
        result = record_today()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("dev_fill"):
            print(f"DEV: filled {result['sessions_green_count']} green session dates")
        elif result.get("dry_run"):
            print(
                f"Dry run: all_green={result['all_green']} "
                f"sessions={result['sessions_green_count']}"
            )
        elif result.get("recorded"):
            print(f"Recorded green session for {result['today']} (total={result['sessions_green_count']})")
        else:
            print(f"Not recorded: {result.get('reason', 'unknown')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
