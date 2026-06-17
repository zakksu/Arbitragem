"""Visual replay tick stream — session candles → animated player frames (10.0 UI)."""

from __future__ import annotations

import hashlib
from typing import Any

from src.integrations.profit_bridge import get_profit_client


def _synthetic_ticks(symbol: str, *, n: int = 90) -> list[dict[str, Any]]:
    sym = symbol.upper()
    seed = int(hashlib.md5(sym.encode()).hexdigest()[:8], 16)
    base = 38.0 if sym.startswith("PETR") else 30.0 + (seed % 50)
    ticks: list[dict[str, Any]] = []
    price = base
    position = 0
    for i in range(n):
        jitter = ((seed + i * 7) % 11 - 5) * 0.02
        price = round(max(0.01, price * (1 + jitter / 100)), 2)
        event = None
        if i == n // 4 and position == 0:
            event = "buy"
            position = 100
        elif i == (3 * n) // 4 and position > 0:
            event = "sell"
            position = 0
        ticks.append(
            {
                "i": i,
                "time": i,
                "price": price,
                "volume": 500 + (seed + i) % 3000,
                "event": event,
                "position": position,
                "pnl": round((price - base) * position * 0.01, 2) if position else 0.0,
            }
        )
    return ticks


def build_replay_ticks(symbol: str, *, limit: int = 120) -> list[dict[str, Any]]:
    """Build tick frames from bridge session candles or synthetic walk."""
    sym = symbol.strip().upper()
    candles = get_profit_client().get_session_candles(sym, bars=limit) or []
    ticks: list[dict[str, Any]] = []
    position = 0
    entry_price = 0.0

    if len(candles) < 3:
        return _synthetic_ticks(sym, n=min(limit, 90))

    for i, bar in enumerate(candles[:limit]):
        try:
            close = float(bar.get("close") or bar.get("c") or 0)
            vol = int(bar.get("volume") or bar.get("v") or 0)
            t = bar.get("time", i)
        except (TypeError, ValueError):
            continue
        if close <= 0:
            continue

        event = None
        if i == len(candles) // 3 and position == 0:
            event = "buy"
            position = 100
            entry_price = close
        elif i == (2 * len(candles)) // 3 and position > 0:
            event = "sell"
            position = 0

        unrealized = round((close - entry_price) * position, 2) if position and entry_price else 0.0
        ticks.append(
            {
                "i": i,
                "time": t,
                "price": close,
                "volume": vol,
                "event": event,
                "position": position,
                "pnl": unrealized,
            }
        )

    return ticks if ticks else _synthetic_ticks(sym, n=min(limit, 90))
