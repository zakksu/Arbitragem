#!/usr/bin/env python3
"""Autonomy autopilot — paper motor cycles until golden path / Phase C progress."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("PAPER_TRADING_MODE", "true")
os.environ.setdefault("AUTO_TRADING_ON_SLEEVES", "true")
os.environ.setdefault("AUTONOMY_ENABLED", "true")
os.environ.setdefault("GOLDEN_PATH_MODE", "true")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run paper motor cycles and report gate progress")
    parser.add_argument("--cycles", type=int, default=5, help="Orchestrator cycles to run")
    parser.add_argument(
        "--fast-track-days",
        type=int,
        default=0,
        help="Spread motor journal across N weekdays (requires AUTONOMY_FAST_TRACK=true)",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from src.config import get_settings
    from src.logging_config import setup_logging
    from src.models import get_session_factory, init_db
    from src.services.autonomy_fast_track import autonomy_gate_snapshot, spread_motor_journal_days
    from src.services.trader_agent import run_trader_cycle
    from src.services.trading_sleeves import set_all

    setup_logging()
    get_settings.cache_clear()
    init_db()
    set_all(True)

    session = get_session_factory()()
    cycle_results: list[dict] = []
    try:
        for i in range(max(1, args.cycles)):
            result = run_trader_cycle(session)
            actions = (result.get("autonomy") or {}).get("actions") or []
            cycle_results.append(
                {
                    "cycle": i + 1,
                    "skipped": result.get("skipped"),
                    "actions": len(actions),
                    "executes": sum(1 for a in actions if a.get("action") == "execute"),
                }
            )

        if args.fast_track_days > 0:
            cycle_results.append(
                {"fast_track": spread_motor_journal_days(session, days=args.fast_track_days)}
            )

        gates = autonomy_gate_snapshot(session)
    finally:
        session.close()

    out = {
        "cycles": cycle_results,
        "gates": {
            "golden_path_all_green": gates["golden_path"].get("all_green"),
            "golden_sessions": gates["golden_path"].get("sessions_green_count"),
            "phase_c_passed": gates["phase_c"].get("passed"),
            "phase_c_criteria": gates["phase_c"].get("criteria"),
            "paper_validation_pass": gates["paper_validation"].get("gate_pass"),
        },
    }

    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        print("-- autonomy autopilot --")
        for c in cycle_results:
            if "fast_track" in c:
                print(f"fast_track: {c['fast_track']}")
            else:
                print(
                    f"cycle {c['cycle']}: actions={c['actions']} executes={c['executes']} "
                    f"skipped={c.get('skipped')}"
                )
        g = out["gates"]
        print(
            f"golden_path: {g['golden_sessions']} green sessions · all_green={g['golden_path_all_green']}"
        )
        print(f"phase_c: passed={g['phase_c_passed']}")
        print(f"paper_validation: pass={g['paper_validation_pass']}")

    passed = out["gates"]["phase_c_passed"] or out["gates"]["golden_path_all_green"]
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
