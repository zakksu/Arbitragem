#!/usr/bin/env python3
"""Background paper motor loop — calls orchestrator until interrupted."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("PAPER_TRADING_MODE", "true")
os.environ.setdefault("AUTO_TRADING_ON_SLEEVES", "true")


def main() -> int:
    parser = argparse.ArgumentParser(description="Paper motor loop")
    parser.add_argument("--interval", type=int, default=0, help="Seconds between cycles (0=config)")
    parser.add_argument("--max-cycles", type=int, default=0, help="Stop after N cycles (0=forever)")
    parser.add_argument("--json", action="store_true", help="Log one JSON line per cycle")
    args = parser.parse_args()

    from src.config import get_settings
    from src.logging_config import setup_logging
    from src.models import init_db
    from src.services.trader_agent import run_trader_cycle
    from src.services.trading_sleeves import set_all
    from src.models import get_session_factory

    setup_logging()
    get_settings.cache_clear()
    init_db()
    set_all(True)

    settings = get_settings()
    interval = args.interval or max(30, int(settings.orchestrator_interval_sec))
    n = 0
    try:
        while True:
            n += 1
            session = get_session_factory()()
            try:
                result = run_trader_cycle(session)
            finally:
                session.close()
            if args.json:
                print(json.dumps({"cycle": n, "result": result}, default=str))
            else:
                actions = (result.get("autonomy") or {}).get("actions") or []
                print(
                    f"[autonomy_loop] cycle {n} skipped={result.get('skipped')} "
                    f"actions={len(actions)}"
                )
            if args.max_cycles and n >= args.max_cycles:
                return 0
            time.sleep(interval)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
