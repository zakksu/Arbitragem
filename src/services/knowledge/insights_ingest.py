"""Ingest B3 archaeology insights JSON into knowledge FTS (11.0 A11.6)."""

from __future__ import annotations

import json
from typing import Any

from src.config import PROJECT_ROOT
from src.services.knowledge.store import ingest_text, knowledge_status

_INSIGHTS = PROJECT_ROOT / "data" / ".dev" / "b3_history_insights.json"


def ingest_b3_insights(*, path: str | None = None, offline: bool = True) -> dict[str, Any]:
    fp = path or str(_INSIGHTS)
    p = PROJECT_ROOT / fp if not fp.startswith("/") and ":" not in fp[:3] else __import__("pathlib").Path(fp)
    if not p.is_file():
        return {"ok": False, "reason": "file_not_found", "path": str(p)}

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"ok": False, "reason": str(exc)}

    summary = data.get("summary") or {}
    core17 = data.get("core17_insights") or {}
    lines = [
        f"B3 archaeology insights — {summary.get('archaeology_trade_count', 0)} trades",
        f"Unique symbols: {summary.get('unique_symbols', 0)}",
        f"Futures rows: {summary.get('futures_count', 0)}",
        f"Cash rows: {summary.get('cash_equity_count', 0)}",
    ]
    for sym, block in list(core17.items())[:20]:
        arch = (block or {}).get("archaeology") or {}
        lines.append(
            f"{sym}: {arch.get('trade_count', 0)} trades, net PnL {arch.get('net_pnl', 0)}, "
            f"win rate {arch.get('win_rate')}"
        )
    text = "\n".join(lines)

    result = ingest_text(
        source_uri=str(p.resolve()),
        text=text,
        title="B3 history insights",
        tags=["archaeology", "b3", "insights"],
        symbols=["PETR4", "VALE3", "WINFUT"],
        offline=offline,
    )
    result["status"] = knowledge_status()
    return result
