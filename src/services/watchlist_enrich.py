"""Watchlist enrichment — ATR%, est. cost, idea score per symbol (4.0-alpha)."""

from __future__ import annotations

from typing import Any

from src.integrations.profit_bridge import get_profit_client
from src.services.idea_score import top_score_by_symbol


def _atr_pct_stub(symbol: str, last: float | None) -> float | None:
    """ATR% stub from bridge or synthetic range."""
    if not last or last <= 0:
        return None
    client = get_profit_client()
    candles = client.get_session_candles(symbol)
    if candles and len(candles) >= 3:
        ranges = [abs(c.get("high", 0) - c.get("low", 0)) for c in candles[-10:]]
        atr = sum(ranges) / len(ranges) if ranges else 0
        return round(atr / last * 100, 2) if last else None
    return round(1.2 + (hash(symbol) % 15) / 10.0, 2)


def _est_cost_brl(last: float | None, cost_per_trade: float = 50.0) -> float:
    if not last:
        return cost_per_trade
    slip_ticks = 2
    tick = 0.01 if last < 50 else 0.05
    return round(cost_per_trade + slip_ticks * tick * 100, 2)


def enrich_watchlist_rows(
    rows: list[dict[str, Any]],
    ideas: list[dict[str, Any]],
    *,
    cost_per_trade_brl: float = 50.0,
) -> list[dict[str, Any]]:
    scores = top_score_by_symbol(ideas)
    out: list[dict[str, Any]] = []
    for row in rows:
        sym = str(row.get("symbol", "")).upper()
        last = row.get("last")
        enriched = dict(row)
        enriched["atr_pct"] = _atr_pct_stub(sym, last)
        enriched["est_cost_brl"] = _est_cost_brl(last, cost_per_trade_brl)
        enriched["idea_score"] = scores.get(sym, 0)
        side = row.get("side_bias") or row.get("side")
        if side == "long":
            enriched["bias"] = "long"
        elif side == "short":
            enriched["bias"] = "short"
        elif scores.get(sym, 0) >= 60:
            enriched["bias"] = "long"
        elif scores.get(sym, 0) <= 30:
            enriched["bias"] = "short"
        else:
            enriched["bias"] = "neutral"
        out.append(enriched)
    out.sort(key=lambda r: r.get("idea_score", 0), reverse=True)
    return out
