"""Paper fill model — spread + 1 tick slippage per leg (S5 / A2.6a)."""

from __future__ import annotations

from src.integrations.profit_bridge import ProfitQuote


def tick_size(price: float | None) -> float:
    if price is None:
        return 0.01
    return 0.01 if price < 50 else 0.05


def paper_fill_price(quote: ProfitQuote | None, side: str, fallback: float | None = None) -> float:
    """Buy pays ask + 1 tick; sell receives bid - 1 tick."""
    side_l = side.lower()
    if quote:
        tick = tick_size(quote.last)
        if side_l == "buy":
            return round(quote.ask + tick, 4)
        if side_l == "sell":
            return round(max(0.01, quote.bid - tick), 4)
        return round(quote.last, 4)
    return float(fallback or 0)
