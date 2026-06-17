"""Outcome ranker — journal patterns for self-learning (10.0-rc)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from src.models import Trade


def rank_outcomes(session: Session, *, symbol: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    q = session.query(Trade)
    if symbol:
        q = q.filter(Trade.symbol == symbol.strip().upper())
    rows = q.order_by(Trade.executed_at.desc()).limit(500).all()

    buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"wins": 0, "losses": 0, "pnl": 0.0, "count": 0}
    )
    for t in rows:
        key = f"{t.symbol}:{t.source}"
        b = buckets[key]
        b["symbol"] = t.symbol
        b["source"] = t.source
        b["count"] += 1
        pnl = float(t.pnl or 0)
        b["pnl"] += pnl
        if pnl >= 0:
            b["wins"] += 1
        else:
            b["losses"] += 1

    ranked = []
    for key, b in buckets.items():
        closed = b["wins"] + b["losses"]
        pf = (b["wins"] / closed) if closed else 0
        ranked.append(
            {
                "key": key,
                "symbol": b["symbol"],
                "source": b["source"],
                "trades": b["count"],
                "win_rate_pct": round(pf * 100, 1),
                "total_pnl": round(b["pnl"], 2),
            }
        )
    ranked.sort(key=lambda x: x["total_pnl"], reverse=True)
    return ranked[:limit]
