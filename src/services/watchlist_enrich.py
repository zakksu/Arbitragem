"""Watchlist enrichment — ATR%, est. cost, composite watch score per symbol."""

from __future__ import annotations

import time
from typing import Any

from src.integrations.profit_bridge import get_profit_client
from src.services.filipe_universe import sector_for
from src.services.crypto_universe import is_crypto
from src.services.futures_universe import is_future
from src.services.idea_score import score_idea, top_score_by_symbol
from src.services.watch_score import score_watchlist_row

_ATR_CACHE: dict[str, tuple[float, float | None]] = {}


def _atr_cache_ttl_sec() -> float:
    from src.services.resource_profile import get_resource_profile

    return get_resource_profile().atr_cache_ttl_sec


def _atr_cache_put(symbol: str, now: float, atr_pct: float | None) -> None:
    from src.services.resource_profile import get_resource_profile, trim_timestamped_cache

    _ATR_CACHE[symbol] = (now, atr_pct)
    trim_timestamped_cache(_ATR_CACHE, get_resource_profile().atr_cache_max_entries)


def _atr_pct_stub(symbol: str, last: float | None, *, bridge_available: bool | None = None) -> float | None:
    """ATR% stub from bridge candles or fast synthetic when bridge offline."""
    if not last or last <= 0:
        return None

    now = time.time()
    cached = _ATR_CACHE.get(symbol)
    if cached and now - cached[0] < _atr_cache_ttl_sec():
        return cached[1]

    from src.config import get_settings

    # Paper / board load: skip per-symbol candle HTTP (14×3s) — use synthetic ATR
    if get_settings().paper_trading_mode:
        atr_pct = round(1.2 + (hash(symbol) % 15) / 10.0, 2)
        _atr_cache_put(symbol, now, atr_pct)
        return atr_pct

    client = get_profit_client()
    use_bridge = bridge_available if bridge_available is not None else client.is_available()
    atr_pct: float | None
    if not use_bridge:
        atr_pct = round(1.2 + (hash(symbol) % 15) / 10.0, 2)
    else:
        candles = client.get_session_candles(symbol)
        if candles and len(candles) >= 3:
            ranges = [abs(c.get("high", 0) - c.get("low", 0)) for c in candles[-10:]]
            atr = sum(ranges) / len(ranges) if ranges else 0
            atr_pct = round(atr / last * 100, 2) if last else None
        else:
            atr_pct = round(1.2 + (hash(symbol) % 15) / 10.0, 2)

    _atr_cache_put(symbol, now, atr_pct)
    return atr_pct


def _est_cost_brl(last: float | None, cost_per_trade: float = 50.0, *, is_fut: bool = False) -> float:
    if is_fut:
        return round(cost_per_trade * 0.6, 2)
    if not last:
        return cost_per_trade
    slip_ticks = 2
    tick = 0.01 if last < 50 else 0.05
    return round(cost_per_trade + slip_ticks * tick * 100, 2)


def _sector_corr_penalty(symbol: str, ideas: list[dict[str, Any]]) -> float:
    sector = (sector_for(symbol) or "").lower()
    if not sector:
        return 0.0
    count = 0
    for idea in ideas:
        if str(idea.get("status", "")) in ("rejected", "executed"):
            continue
        sym = str(idea.get("symbol", "")).upper()
        if sym == symbol.upper():
            continue
        if (sector_for(sym) or "").lower() == sector:
            count += 1
    if count <= 2:
        return 0.0
    return float((count - 2) * 4)


def enrich_watchlist_rows(
    rows: list[dict[str, Any]],
    ideas: list[dict[str, Any]],
    *,
    cost_per_trade_brl: float = 50.0,
) -> list[dict[str, Any]]:
    open_stack = [i for i in ideas if i.get("status") not in ("rejected", "executed")]
    idea_scores = top_score_by_symbol(ideas, open_stack=open_stack)
    client = get_profit_client()
    bridge_ok = client.is_available()
    out: list[dict[str, Any]] = []
    for row in rows:
        sym = str(row.get("symbol", "")).upper()
        last = row.get("last")
        fut = is_future(sym) or row.get("asset_class") == "future"
        crypto = is_crypto(sym) or row.get("asset_class") == "crypto"
        enriched = dict(row)
        if crypto:
            enriched["asset_class"] = "crypto"
            enriched["read_only"] = True
            enriched["auto_trade"] = False
        elif fut:
            enriched["asset_class"] = "future"
        else:
            enriched["asset_class"] = row.get("asset_class", "equity")
        enriched["atr_pct"] = _atr_pct_stub(sym, last, bridge_available=bridge_ok)
        if fut and last and last > 1000:
            enriched["atr_pct"] = round(0.35 + (hash(sym) % 8) / 10.0, 2)
        elif crypto and last:
            enriched["atr_pct"] = round(1.5 + (hash(sym) % 20) / 10.0, 2)
        cost = _est_cost_brl(last, cost_per_trade_brl, is_fut=fut)
        enriched["est_cost_brl"] = cost
        base_idea_score = idea_scores.get(sym, 0)
        enriched["idea_score"] = base_idea_score

        quote = {
            "last": last,
            "bid": row.get("bid"),
            "ask": row.get("ask"),
        }
        sector_pen = _sector_corr_penalty(sym, open_stack)
        enriched["watch_score"] = score_watchlist_row(
            sym,
            quote,
            row,
            base_idea_score,
            sector_corr_penalty=sector_pen,
            cost_brl=cost,
        )
        side = row.get("side_bias") or row.get("side")
        ws = enriched["watch_score"]
        if side == "long":
            enriched["bias"] = "long"
        elif side == "short":
            enriched["bias"] = "short"
        elif ws >= 60:
            enriched["bias"] = "long"
        elif ws <= 30:
            enriched["bias"] = "short"
        else:
            enriched["bias"] = "neutral"
        out.append(enriched)
    out.sort(key=lambda r: r.get("watch_score", r.get("idea_score", 0)), reverse=True)
    return out
