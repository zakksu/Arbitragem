#!/usr/bin/env python3
"""Pre-market autonomy + replay smoke test for B3 open."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import get_settings
from src.logging_config import setup_logging
from src.models import get_session_factory, init_db
from src.services.autonomy import autonomy_status, run_autonomy_cycle
from src.services.replay_lab import start_replay
from src.services.scanner import PatternScanner
from src.services.trade_ideas import TradeIdeaService
from src.services.trading_sleeves import set_all, status as sleeves_status


def main() -> int:
    os.environ.setdefault("PAPER_TRADING_MODE", "true")
    setup_logging()
    get_settings.cache_clear()
    init_db()
    set_all(True)

    summary: dict = {"sleeves": sleeves_status(), "replay": None, "autonomy": None, "scan": 0}

    session = get_session_factory()()
    try:
        print("[autonomy_today] Core14 scan...")
        hits = PatternScanner(session).run_daily_scan()
        summary["scan"] = len(hits)
        TradeIdeaService(session).generate_from_latest_scan(limit=8)

        print("[autonomy_today] Replay lab job...")
        from src.services.structure_types import replay_strategy_for_structure

        summary["replay"] = start_replay(
            strategy=replay_strategy_for_structure("stock_scalp_vwap"),
            symbol="PETR4",
            speed=10.0,
        )

        settings = get_settings()
        if settings.autonomy_enabled:
            print("[autonomy_today] Running autonomy cycle...")
            summary["autonomy"] = run_autonomy_cycle(session)
        else:
            summary["autonomy"] = {"skipped": "AUTONOMY_ENABLED=false"}
            print("[autonomy_today] Autonomy disabled — set AUTONOMY_ENABLED=true in .env")
    finally:
        session.close()

    summary["status"] = autonomy_status()
    print("\n-- autonomy_today summary --")
    print(json.dumps(summary, indent=2, default=str))
    print("\nProfitChart: import NTSL from exports/profit/, arm strategy in Editor, run replay.")
    print("Board: http://localhost:8000/board  |  Strategies: http://localhost:8000/board/strategies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
