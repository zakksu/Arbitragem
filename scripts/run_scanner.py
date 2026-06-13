#!/usr/bin/env python3
"""CLI: trigger daily pattern scan."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.logging_config import setup_logging
from src.models import get_session_factory, init_db
from src.services.scanner import PatternScanner


def main():
    setup_logging()
    init_db()
    session = get_session_factory()()
    try:
        results = PatternScanner(session).run_daily_scan()
        for r in results:
            print(f"{r.symbol}: tags={r.pattern_tags} spike={r.spike_score}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
