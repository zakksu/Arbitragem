"""Paper fill model — spread + 1 tick slippage per leg (S5 / A2.6a / 4.0-rc)."""

from __future__ import annotations

from typing import Any

from src.integrations.profit_bridge import ProfitQuote


def tick_size(price: float | None, symbol: str | None = None) -> float:
    if symbol:
        return crypto_tick_size(symbol, price)
    if price is None:
        return 0.01
    return 0.01 if price < 50 else 0.05


def crypto_tick_size(symbol: str, price: float | None = None) -> float:
    sym = symbol.upper()
    if sym in ("BTC", "ETH"):
        return 0.01
    if sym == "SOL":
        return 0.001
    if sym.startswith("WIN"):
        return 5.0
    if sym.startswith("WDO"):
        return 0.001
    return tick_size(price, symbol=None)


def paper_fill_price(quote: ProfitQuote | None, side: str, fallback: float | None = None) -> float:
    """Buy pays ask + 1 tick; sell receives bid - 1 tick."""
    side_l = side.lower()
    sym = quote.symbol if quote else None
    if quote:
        tick = tick_size(quote.last, sym)
        if side_l == "buy":
            return round(quote.ask + tick, 4)
        if side_l == "sell":
            return round(max(0.01, quote.bid - tick), 4)
        return round(quote.last, 4)
    return float(fallback or 0)


def ideal_fill_price(quote: ProfitQuote | None, side: str, fallback: float | None = None) -> float:
    """Mid/last reference before slippage — for confirm modal comparison."""
    if quote:
        if side.lower() == "buy":
            return round(quote.last, 4)
        if side.lower() == "sell":
            return round(quote.last, 4)
        return round(quote.last, 4)
    return float(fallback or 0)


def estimate_leg_fill(
    *,
    symbol: str,
    side: str,
    quantity: int,
    entry_price: float | None = None,
    quote: ProfitQuote | None = None,
) -> dict[str, Any]:
    if quote is None:
        from src.services.crypto_paper import quote_for_symbol

        quote = quote_for_symbol(symbol)
    ideal = ideal_fill_price(quote, side, entry_price)
    expected = paper_fill_price(quote, side, entry_price)
    tick = tick_size(ideal or entry_price, symbol)
    slip_ticks = round(abs(expected - ideal) / tick, 2) if tick else 0.0
    slip_brl = round(abs(expected - ideal) * quantity, 2)
    return {
        "symbol": symbol.upper(),
        "side": side,
        "quantity": quantity,
        "ideal_price": ideal,
        "expected_fill": expected,
        "slippage_ticks": slip_ticks,
        "slippage_brl": slip_brl,
        "quote_bid": quote.bid if quote else None,
        "quote_ask": quote.ask if quote else None,
    }


def estimate_paper_fills(
    idea: dict[str, Any],
    *,
    entry_price: float | None = None,
) -> dict[str, Any]:
    """Expected vs ideal fill preview for confirm modal (A4.16)."""
    legs_in = idea.get("legs") or [
        {
            "symbol": idea.get("symbol"),
            "side": "buy" if str(idea.get("side", "long")).lower() == "long" else "sell",
            "quantity": 100,
        }
    ]
    entry = entry_price or idea.get("entry_price")
    leg_fills: list[dict[str, Any]] = []
    for leg in legs_in:
        side = leg.get("side", "buy")
        if side == "flat":
            continue
        leg_fills.append(
            estimate_leg_fill(
                symbol=str(leg.get("symbol", idea.get("symbol", ""))),
                side=side,
                quantity=int(leg.get("quantity", 100)),
                entry_price=entry,
            )
        )
    total_slip = round(sum(l["slippage_brl"] for l in leg_fills), 2)
    return {
        "slippage_model": "spread_plus_1_tick",
        "legs": leg_fills,
        "total_slippage_brl": total_slip,
        "paper_trading_mode": True,
    }
