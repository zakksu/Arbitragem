"""Session VWAP helpers — A2.5b scanner + symbol panel."""

from __future__ import annotations

from typing import Any


def session_vwap(candles: list[dict[str, Any]]) -> float | None:
    """Volume-weighted average price from session candles."""
    if not candles:
        return None
    num = 0.0
    den = 0.0
    for bar in candles:
        try:
            high = float(bar.get("high") or bar.get("h") or 0)
            low = float(bar.get("low") or bar.get("l") or 0)
            close = float(bar.get("close") or bar.get("c") or 0)
            vol = float(bar.get("volume") or bar.get("v") or 0)
        except (TypeError, ValueError):
            continue
        if vol <= 0:
            continue
        typical = (high + low + close) / 3.0 if high and low else close
        if typical <= 0:
            continue
        num += typical * vol
        den += vol
    if den <= 0:
        return None
    return round(num / den, 4)


def vwap_context(
    *,
    last: float | None,
    prev_last: float | None,
    vwap: float | None,
) -> dict[str, Any]:
    """Distance + reclaim flags for scanner/symbol panel."""
    if last is None or vwap is None or vwap <= 0:
        return {
            "session_vwap": vwap,
            "vwap_distance_pct": None,
            "vwap_reclaim_long": False,
            "vwap_reclaim_short": False,
        }
    dist = round((last - vwap) / vwap * 100, 3)
    reclaim_long = bool(prev_last is not None and prev_last < vwap <= last)
    reclaim_short = bool(prev_last is not None and prev_last > vwap >= last)
    return {
        "session_vwap": vwap,
        "vwap_distance_pct": dist,
        "vwap_reclaim_long": reclaim_long,
        "vwap_reclaim_short": reclaim_short,
    }


def build_session_vwap_payload(symbol: str) -> dict[str, Any]:
    """Session VWAP bundle for symbol panel (A2.5b API)."""
    from src.integrations.profit_bridge import get_profit_client

    sym = symbol.strip().upper()
    client = get_profit_client()
    quote = client.get_quote(sym)
    candles = client.get_session_candles(sym)
    vwap = session_vwap(candles)
    last = quote.last if quote else None
    ctx = vwap_context(last=last, prev_last=None, vwap=vwap)
    return {
        "symbol": sym,
        "last": last,
        "bid": quote.bid if quote else None,
        "ask": quote.ask if quote else None,
        **ctx,
    }
