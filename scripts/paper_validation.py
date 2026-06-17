#!/usr/bin/env python3
"""Paper week validation gate — 4.0.0 GA checklist."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models import get_session_factory, init_db
from src.services.paper_validation import (
    build_paper_validation,
    build_journal_export,
    write_journal_csv,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Paper week #3 validation gate")
    parser.add_argument(
        "--export",
        choices=("json", "csv", "none"),
        default="none",
        help="Export journal alongside checklist",
    )
    args = parser.parse_args()

    init_db()
    session = get_session_factory()()
    try:
        report = build_paper_validation(session)
        if args.export == "json":
            report["journal"] = build_journal_export(session)
        elif args.export == "csv":
            report["journal_file"] = write_journal_csv(session)
        print(json.dumps(report, indent=2))
        return 0 if report["gate_pass"] else 2
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
