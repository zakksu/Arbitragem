#!/usr/bin/env python3
"""Pre-market session prep — one command before B3 open."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Arbitragem session prep (paper or manual Profit)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--during", action="store_true", help="Print during-market steps only")
    args = parser.parse_args()

    from src.models import get_session_factory, init_db
    from src.services.session_prep import build_session_prep

    init_db()
    session = get_session_factory()()
    try:
        prep = build_session_prep(session)
    finally:
        session.close()

    if args.json:
        print(json.dumps(prep, indent=2))
        return 0 if prep["ready_paper_session"] or prep["ready_manual_session"] else 2

    if args.during:
        mode = prep["active_execution_mode"]
        steps = (
            prep["steps_during_paper"]
            if prep["paper_trading_mode"]
            else prep["steps_during_manual"]
        )
        print(f"\n=== DURING MARKET ({mode}) ===\n")
        for row in steps:
            print(f"  {row['step']}. {row['action']}")
        return 0

    print("\n=== ARBITRAGEM SESSION PREP ===\n")
    print(f"Mode: {prep['active_execution_mode']}  |  Paper: {prep['paper_trading_mode']}")
    print(f"Ready paper: {prep['ready_paper_session']}  |  Ready manual: {prep['ready_manual_session']}")
    if prep["blockers"]:
        print(f"Blockers: {', '.join(prep['blockers'])}")
    print(f"Day P&L: R$ {prep['risk']['day_pnl_brl']:.2f}  |  Phase C days: {prep['phase_c'].get('paper_days')}/{prep['phase_c'].get('target_days')}")
    print(f"Outbox pending: {prep['outbox_pending']}")

    print("\n--- PRE-MARKET (do in order) ---")
    for i, step in enumerate(prep["steps_pre"], 1):
        mark = "OK" if step["ok"] else "!!"
        print(f"  [{mark}] {i}. {step['label']}")
        print(f"       {step['cmd']}")
        if step.get("detail"):
            print(f"       -> {step['detail']}")

    steps = (
        prep["steps_during_paper"]
        if prep["paper_trading_mode"]
        else prep["steps_during_manual"]
    )
    print("\n--- DURING MARKET ---")
    for row in steps:
        print(f"  {row['step']}. {row['action']}")

    print("\n--- QUICK COMMANDS ---")
    for k, v in prep["quick_commands"].items():
        print(f"  {k}: {v}")
    print(f"\nBoard: {prep['board_url']}\n")

    return 0 if prep["ready_paper_session"] or prep["ready_manual_session"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
