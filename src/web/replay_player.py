"""Visual replay tick stream — session candles + replay engine fills (10.0 UI)."""

from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy.orm import Session

from src.integrations.profit_bridge import get_profit_client
from src.services.replay_engine import get_replay, list_recent_sessions
from src.services.strategy_store import list_stored_strategies


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


def _apply_fills(ticks: list[dict[str, Any]], fills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not fills or not ticks:
        return ticks
    by_idx: dict[int, dict[str, Any]] = {}
    for f in fills:
        idx = f.get("tick_index")
        if idx is None:
            continue
        by_idx[int(idx)] = f

    position = 0
    entry = 0.0
    out: list[dict[str, Any]] = []
    for t in ticks:
        row = dict(t)
        fill = by_idx.get(int(row["i"]))
        if fill:
            side = (fill.get("side") or "").lower()
            if side in ("buy", "cover"):
                row["event"] = "buy"
                position = int(fill.get("quantity") or 100)
                entry = float(fill.get("price") or row["price"])
            elif side in ("sell", "short"):
                row["event"] = "sell"
                position = 0
        row["position"] = position
        if position and entry:
            row["pnl"] = round((float(row["price"]) - entry) * position, 2)
        else:
            row["pnl"] = float(fill.get("pnl") or 0) if fill else 0.0
        out.append(row)
    return out


def build_replay_ticks(symbol: str, *, limit: int = 120, fills: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Build tick frames from bridge session candles or synthetic walk."""
    sym = symbol.strip().upper()
    candles = get_profit_client().get_session_candles(sym, bars=limit) or []
    ticks: list[dict[str, Any]] = []
    position = 0
    entry_price = 0.0

    if len(candles) < 3:
        ticks = _synthetic_ticks(sym, n=min(limit, 90))
        return _apply_fills(ticks, fills or [])

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
        if not fills:
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

    ticks = ticks if ticks else _synthetic_ticks(sym, n=min(limit, 90))
    return _apply_fills(ticks, fills or [])


def build_replay_player_context(
    session: Session,
    symbol: str,
    *,
    speed: int = 8,
    job_id: str | None = None,
    last_run: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sym = symbol.strip().upper()
    fills: list[dict[str, Any]] = []
    run = last_run
    if job_id:
        run = get_replay(job_id, session=session) or run
    if run:
        fills = run.get("fills") or []

    strategies = list_stored_strategies(session, limit=30)
    sessions = list_recent_sessions(session, limit=8)
    default_strategy = "scalp_default"
    if strategies:
        default_strategy = strategies[0]["name"]

    return {
        "symbol": sym,
        "speed": speed,
        "ticks": build_replay_ticks(sym, fills=fills),
        "strategies": strategies,
        "sessions": sessions,
        "default_strategy": default_strategy,
        "last_run": run,
        "job_id": job_id or (run.get("job_id") if run else None),
    }
