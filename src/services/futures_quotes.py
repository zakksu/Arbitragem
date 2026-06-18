"""Futures quote stubs — WIN/WDO with B3 session badges (4.1 A4.20)."""

from __future__ import annotations

import hashlib
from datetime import datetime, time
from zoneinfo import ZoneInfo

from src.integrations.profit_bridge import ProfitQuote, get_profit_client
from src.services.futures_universe import FutureSymbol, load_futures_universe, symbol_list

_B3_TZ = ZoneInfo("America/Sao_Paulo")
_FUTURES_OPEN = time(9, 0)
_FUTURES_CLOSE = time(18, 25)
_WEEKEND = {5, 6}


def _seed(symbol: str) -> int:
    return int(hashlib.md5(symbol.upper().encode()).hexdigest()[:8], 16)


def futures_session_status(now: datetime | None = None) -> dict[str, str]:
    """B3 futures day session badge for watchlist rows."""
    local = (now or datetime.now(_B3_TZ)).astimezone(_B3_TZ)
    if local.weekday() in _WEEKEND:
        return {"session_status": "closed", "session_label": "Weekend", "market": "b3_futures"}
    t = local.time()
    if _FUTURES_OPEN <= t < _FUTURES_CLOSE:
        return {"session_status": "open", "session_label": "B3 day", "market": "b3_futures"}
    if t < _FUTURES_OPEN:
        return {"session_status": "pre", "session_label": "Pre-open", "market": "b3_futures"}
    return {"session_status": "closed", "session_label": "After-hours", "market": "b3_futures"}


def _stub_quote(fut: FutureSymbol) -> ProfitQuote:
    seed = _seed(fut.symbol)
    if fut.symbol == "WINFUT":
        last = round(128_000 + (seed % 4000) - 2000 + (datetime.utcnow().hour % 12) * 15, 0)
        spread = 10.0
    else:
        last = round(5.45 + (seed % 200) / 1000.0 + (datetime.utcnow().minute % 30) / 1000.0, 3)
        spread = 0.001
    bid = round(last - spread / 2, 3 if fut.symbol == "WDOFUT" else 0)
    ask = round(last + spread / 2, 3 if fut.symbol == "WDOFUT" else 0)
    return ProfitQuote(
        symbol=fut.symbol,
        bid=bid,
        ask=ask,
        last=last,
        volume=80_000 + seed % 500_000,
        timestamp=datetime.utcnow(),
    )


def get_futures_quotes(symbols: list[str] | None = None) -> dict[str, ProfitQuote]:
    wanted = {s.upper() for s in (symbols or symbol_list())}
    out: dict[str, ProfitQuote] = {}
    client = get_profit_client()
    if client.is_available():
        bridge = client.get_quotes_batch(list(wanted))
        for sym, q in bridge.items():
            if sym in wanted and sym in symbol_list():
                out[sym] = q
    for fut in load_futures_universe():
        if fut.symbol not in wanted:
            continue
        if fut.symbol not in out:
            stub = _stub_quote(fut)
            from src.services.futures_roll import resolve_futures_quote_symbol

            meta = resolve_futures_quote_symbol(fut.symbol)
            if meta.get("resolved") and meta["resolved"] != fut.symbol:
                stub.symbol = fut.symbol
            out[fut.symbol] = stub
    return out


def build_futures_watchlist_rows() -> list[dict]:
    """Base rows for futures before watchlist enrichment."""
    session = futures_session_status()
    quotes = get_futures_quotes()
    rows: list[dict] = []
    for fut in load_futures_universe():
        q = quotes.get(fut.symbol)
        row = fut.to_dict()
        row.update(session)
        from src.services.futures_roll import resolve_futures_quote_symbol

        roll = resolve_futures_quote_symbol(fut.symbol)
        if roll.get("resolved"):
            row["front_month"] = roll["resolved"]
            row["roll_root"] = roll.get("root")
        if q:
            row["last"] = q.last
            row["bid"] = q.bid
            row["ask"] = q.ask
            row["volume"] = q.volume
            row["quote_source"] = "profit" if get_profit_client().is_available() else "stub"
        else:
            row["quote_source"] = "stub"
        rows.append(row)
    return rows
