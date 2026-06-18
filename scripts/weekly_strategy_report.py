#!/usr/bin/env python3
"""Run weekly strategy tick simulation and print performance report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Weekly strategy simulation report")
    parser.add_argument("--days", type=int, default=7, help="Trailing window (default 7)")
    parser.add_argument("--run", action="store_true", help="Run fresh tick sims on session candles")
    parser.add_argument("--max-fresh", type=int, default=25, help="Max new sim pairs when --run")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--out", type=str, default="", help="Write markdown report to path")
    args = parser.parse_args()

    from src.models import get_session_factory, init_db
    from src.services.weekly_strategy_sim import (
        build_weekly_strategy_report,
        format_weekly_report_markdown,
    )

    init_db()
    session = get_session_factory()()
    try:
        report = build_weekly_strategy_report(
            session,
            days=args.days,
            run_sim=args.run,
            max_fresh=args.max_fresh,
        )
    finally:
        session.close()

    md = format_weekly_report_markdown(report)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md, encoding="utf-8")
        print(f"Wrote {out_path}", flush=True)

    if args.as_json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(md, flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
