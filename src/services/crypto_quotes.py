"""Binance public REST quotes for BTC/ETH/SOL (4.2 A4.23)."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime

import httpx

from src.config import get_settings
from src.integrations.profit_bridge import ProfitQuote
from src.services.crypto_universe import CryptoSymbol, load_crypto_universe, symbol_list

_CACHE_TS: float = 0.0
_CACHE_QUOTES: dict[str, ProfitQuote] = {}
_LAST_QUOTE_SOURCE: str = "stub"

_STUB_BASE: dict[str, float] = {
    "BTC": 95_000.0,
    "ETH": 3_500.0,
    "SOL": 150.0,
}


def _seed(symbol: str) -> int:
    return int(hashlib.md5(symbol.upper().encode()).hexdigest()[:8], 16)


def _stub_quote(coin: CryptoSymbol) -> ProfitQuote:
    seed = _seed(coin.symbol)
    base = _STUB_BASE.get(coin.symbol, 100.0)
    jitter = (seed % 200) / 100.0 - 1.0
    last = round(base + jitter + (datetime.now(UTC).minute % 30) * 0.05, 2)
    spread = last * 0.0002
    return ProfitQuote(
        symbol=coin.symbol,
        bid=round(last - spread / 2, 2),
        ask=round(last + spread / 2, 2),
        last=last,
        volume=10_000 + seed % 500_000,
        timestamp=datetime.now(UTC),
    )


def _fetch_binance_quotes(pairs: list[str]) -> dict[str, dict]:
    settings = get_settings()
    if not settings.binance_quotes_enabled or not pairs:
        return {}
    url = f"{settings.binance_api_base.rstrip('/')}/api/v3/ticker/24hr"
    params = {"symbols": json.dumps(pairs)}
    try:
        with httpx.Client(timeout=4.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                return {}
            data = resp.json()
            if not isinstance(data, list):
                return {}
            return {str(row.get("symbol", "")).upper(): row for row in data if row.get("symbol")}
    except httpx.HTTPError:
        return {}


def get_crypto_quotes(symbols: list[str] | None = None) -> dict[str, ProfitQuote]:
    """Return BTC/ETH/SOL quotes — Binance when reachable, else stubs."""
    global _CACHE_TS, _CACHE_QUOTES, _LAST_QUOTE_SOURCE

    wanted = {s.upper() for s in (symbols or symbol_list())}
    now = time.time()
    from src.services.resource_profile import get_resource_profile

    cache_ttl = get_resource_profile().crypto_cache_ttl_sec
    if _CACHE_QUOTES and now - _CACHE_TS < cache_ttl:
        cached = {k: v for k, v in _CACHE_QUOTES.items() if k in wanted}
        if len(cached) == len(wanted):
            return cached

    coins = [c for c in load_crypto_universe() if c.symbol in wanted]
    pair_map = {c.binance_pair: c for c in coins}
    binance = _fetch_binance_quotes(list(pair_map))
    _LAST_QUOTE_SOURCE = "binance" if binance else "stub"
    out: dict[str, ProfitQuote] = {}

    for pair, coin in pair_map.items():
        row = binance.get(pair.upper())
        if row:
            try:
                last = float(row.get("lastPrice") or row.get("weightedAvgPrice") or 0)
                bid = float(row.get("bidPrice") or last)
                ask = float(row.get("askPrice") or last)
                volume = int(float(row.get("volume") or 0))
            except (TypeError, ValueError):
                out[coin.symbol] = _stub_quote(coin)
                continue
            if last <= 0:
                out[coin.symbol] = _stub_quote(coin)
                continue
            out[coin.symbol] = ProfitQuote(
                symbol=coin.symbol,
                bid=bid,
                ask=ask,
                last=last,
                volume=volume,
                timestamp=datetime.now(UTC),
            )
        else:
            out[coin.symbol] = _stub_quote(coin)

    _CACHE_TS = now
    _CACHE_QUOTES = dict(out)
    return out


def build_crypto_watchlist_rows() -> list[dict]:
    quotes = get_crypto_quotes()
    rows: list[dict] = []
    for coin in load_crypto_universe():
        q = quotes.get(coin.symbol)
        row = coin.to_dict()
        row["sector"] = "Crypto"
        row["market"] = "binance_spot"
        if q:
            row["last"] = q.last
            row["bid"] = q.bid
            row["ask"] = q.ask
            row["volume"] = q.volume
        row["quote_source"] = _LAST_QUOTE_SOURCE
        rows.append(row)
    return rows
