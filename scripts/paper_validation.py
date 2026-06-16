#!/usr/bin/env python3
"""Paper week validation gate — 4.0.0 GA checklist."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models import Trade, get_session_factory, init_db
from src.models import TradeIdea


def main() -> int:
    init_db()
    session = get_session_factory()()
    try:
        confirms = session.query(TradeIdea).filter(TradeIdea.status.in_(["confirmed", "executed"])).count()
        trades = session.query(Trade).count()
        products = session.query(TradeIdea).filter(TradeIdea.rationale.isnot(None)).count()
        report = {
            "structure_confirms": confirms,
            "journal_trades": trades,
            "trade_products_journaled": products,
            "gate_pass": confirms >= 10 and products >= 3,
            "note": "Paper week #3 — run after 10+ confirms and 3 Trade Products journaled",
        }
        print(json.dumps(report, indent=2))
        return 0 if report["gate_pass"] else 2
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
