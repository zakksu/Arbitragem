"""Watchlist composite score 0–100 — idea quality × liquidity × cost."""

from __future__ import annotations

from typing import Any

from src.services.idea_score import score_idea


def score_watchlist_row(
    symbol: str,
    quote: dict[str, Any] | None,
    scan: dict[str, Any] | None,
    idea_score: int,
    *,
    sector_corr_penalty: float = 0.0,
    cost_brl: float = 50.0,
) -> int:
    """
    Composite watchlist rank (0–100).

    Formula:
      base = idea_score (0–100 from idea_score.py)
      liquidity = +5 if volume spike tag or scan spike_score >= 35 else 0
      spread_pen = −min(20, spread_pct / 0.15 × 12) when spread > 0.15% of mid
      cost_pen = −min(15, cost_brl / notional × 100) when notional > 0
      sector_pen = −sector_corr_penalty (0–15 from duplicate sector ideas)
      final = clamp(base + liquidity − spread_pen − cost_pen − sector_pen, 0, 100)
    """
    base = max(0, min(100, int(idea_score)))
    bonus = 0.0
    spread_pen = 0.0
    cost_pen = 0.0

    last = None
    bid = ask = None
    if quote:
        last = quote.get("last") or quote.get("close")
        bid = quote.get("bid")
        ask = quote.get("ask")
    if scan:
        spike = float(scan.get("spike_score") or 0)
        if spike >= 35:
            bonus += 5.0

    mid = last
    if bid and ask and bid > 0 and ask > 0:
        mid = (float(bid) + float(ask)) / 2.0
        spread = float(ask) - float(bid)
        if mid > 0:
            spread_pct = spread / mid * 100.0
            if spread_pct > 0.15:
                spread_pen = min(20.0, spread_pct / 0.15 * 12.0)

    notional = (float(mid) * 100.0) if mid else 0.0
    if notional > 0 and cost_brl > 0:
        cost_pen = min(15.0, cost_brl / notional * 100.0)

    sector_pen = min(15.0, max(0.0, float(sector_corr_penalty)))
    raw = base + bonus - spread_pen - cost_pen - sector_pen
    return max(0, min(100, int(round(raw))))
