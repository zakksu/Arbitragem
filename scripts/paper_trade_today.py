#!/usr/bin/env python3
"""Paper-trade today's market: scan Core14, confirm + execute top gated ideas."""

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
from src.services.scanner import PatternScanner
from src.services.trade_ideas import TradeIdeaService

MAX_CONFIRM = int(os.environ.get("PAPER_TRADE_MAX", "2"))


def main() -> int:
    os.environ.setdefault("PAPER_TRADING_MODE", "true")
    setup_logging()
    get_settings.cache_clear()
    init_db()

    summary: dict = {"scanned": 0, "ideas": [], "confirmed": [], "executed": []}

    session = get_session_factory()()
    try:
        settings = get_settings()
        if settings.execution_backend == "clear":
            print("[paper] Refusing to run: execution_backend=clear (paper only).")
            return 1

        print("[paper] Running Core14 scanner (in-process)...")
        scan_rows = PatternScanner(session).run_daily_scan()
        summary["scanned"] = len(scan_rows)
        print(f"       scan hits: {summary['scanned']}")

        svc = TradeIdeaService(session)
        svc.generate_from_latest_scan(limit=12)
        ideas = svc.list_ideas(limit=30)
        summary["ideas"] = [
            {"id": i.id, "symbol": i.symbol, "status": i.status} for i in ideas
        ]

        candidates = [
            i
            for i in ideas
            if i.status in ("backtested", "detected") and i.backtest_proof
            and svc.passes_backtest_gate(i.backtest_proof)
        ]
        candidates.sort(key=lambda i: float(i.reliability or 0), reverse=True)

        for idea in candidates[:MAX_CONFIRM]:
            sym = idea.symbol
            print(f"[paper] Confirming idea #{idea.id} ({sym})...")
            try:
                confirmed = svc.confirm_idea(idea.id)
            except ValueError as exc:
                print(f"       confirm skipped: {exc}")
                continue
            summary["confirmed"].append(
                {"id": idea.id, "symbol": sym, "status": confirmed.status}
            )

            print(f"[paper] Executing paper fill for #{idea.id}...")
            try:
                executed = svc.execute_idea(idea.id)
            except ValueError as exc:
                print(f"       execute skipped: {exc}")
                continue
            summary["executed"].append(
                {"id": idea.id, "symbol": sym, "status": executed.status}
            )
    finally:
        session.close()

    print("\n-- Paper trade summary --")
    print(json.dumps(summary, indent=2))
    print("\nBoard: http://localhost:8000/board  |  Journal: dashboard -> Journal")
    return 0 if summary["executed"] else (0 if summary["confirmed"] else 1)


if __name__ == "__main__":
    raise SystemExit(main())
