#!/usr/bin/env python3
"""CLI — run Profit Replay batch for Core5 + WIN/WDO (13.0-beta)."""

from __future__ import annotations

import argparse
import json
import sys

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models import get_session_factory, init_db
from src.services.replay_batch import run_replay_batch


def main() -> int:
    p = argparse.ArgumentParser(description="Replay batch — Core5 + futures")
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-promote", action="store_true")
    p.add_argument("--speed", type=float, default=10.0)
    args = p.parse_args()

    init_db()
    session = get_session_factory()()
    try:
        result = run_replay_batch(
            session,
            auto_promote=not args.no_promote,
            speed=args.speed,
        )
    finally:
        session.close()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"Replay runs: {result['runs']}, errors: {len(result['errors'])}")
        if result.get("promotion"):
            print(f"WFO promoted: {result['promotion'].get('promoted', 0)}")
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
