#!/usr/bin/env python3
"""Import Filipe B3 full-history Excel into archaeology + write insights JSON."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings
from src.models import Trade, get_session_factory, init_db
from src.services.archaeology_backtest import archaeology_symbol_insights
from src.services.b3_history_import import import_b3_history_excel, preview_excel_rows


def _summarize_trades(session, *, top_n: int = 25) -> dict:
    rows = session.query(Trade).filter(Trade.source == "archaeology").all()
    syms = Counter(t.symbol for t in rows)
    cash_like = [s for s in syms if len(s) == 5 and s[-1].isdigit()]
    fut_like = [s for s in syms if s.startswith(("WIN", "WDO", "IND", "DOL"))]
    opt_like = [s for s in syms if len(s) > 5]
    return {
        "archaeology_trade_count": len(rows),
        "unique_symbols": len(syms),
        "top_symbols": syms.most_common(top_n),
        "cash_equity_count": sum(syms[s] for s in cash_like),
        "futures_count": sum(syms[s] for s in fut_like),
        "options_count": sum(syms[s] for s in opt_like),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import B3 history Excel")
    parser.add_argument("path", nargs="?", help="Path to .xlsx (default: Downloads)")
    parser.add_argument("--copy-to", default=str(PROJECT_ROOT / "exports" / "archaeology"))
    parser.add_argument("--insights-out", default=str(PROJECT_ROOT / "data" / ".dev" / "b3_history_insights.json"))
    parser.add_argument("--preview-only", action="store_true")
    args = parser.parse_args()

    src = Path(args.path) if args.path else Path.home() / "Downloads" / "historico b3 full.xlsx"
    if not src.exists():
        print(f"File not found: {src}", file=sys.stderr)
        return 1

    preview = preview_excel_rows(src, limit=3)
    print(json.dumps({"preview": preview}, indent=2, default=str))
    if args.preview_only:
        return 0

    dest_dir = Path(args.copy_to)
    dest_dir.mkdir(parents=True, exist_ok=True)
    archive = dest_dir / src.name
    if src.resolve() != archive.resolve():
        shutil.copy2(src, archive)

    init_db()
    session = get_session_factory()()
    try:
        result = import_b3_history_excel(session, archive)
        session.commit()
        summary = _summarize_trades(session)
        core17 = ["PETR4", "VALE3", "PRIO3", "ITUB4", "BBAS3", "BBDC4", "BBSE3", "B3SA3",
                  "ABEV3", "GGBR4", "CSNA3", "USIM5", "SUZB3", "WEGE3", "BOVA11", "RADL3", "MGLU3"]
        insights = {
            "import": result,
            "summary": summary,
            "core17_insights": {
                sym: archaeology_symbol_insights(session, sym) for sym in core17
            },
        }
        out = Path(args.insights_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(insights, indent=2, default=str), encoding="utf-8")
        print(json.dumps({"ok": True, "insights_path": str(out), **result}, indent=2, default=str))
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
