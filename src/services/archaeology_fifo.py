"""FIFO round-trip P&L for archaeology legs (11.0 A11.1)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.models import Trade


def trade_lane(symbol: str) -> str:
    s = symbol.strip().upper()
    if s.startswith(("WIN", "WDO", "BIT", "MBR", "IND", "DOL")):
        return "futures"
    if len(s) > 6:
        return "options"
    return "cash"


@dataclass
class _Lot:
    qty: int
    price: float
    fees: float
    executed_at: datetime | None
    trade_id: int | None


def _side_is_buy(side: str | None) -> bool:
    val = (side or "buy").strip().lower()
    return val in ("buy", "b", "c", "compra", "long")


def fifo_realized_trips(trades: list[Trade]) -> list[dict[str, Any]]:
    """Match buy/sell legs per symbol with FIFO; return closed round trips."""
    by_symbol: dict[str, list[Trade]] = {}
    for t in trades:
        by_symbol.setdefault(t.symbol.upper(), []).append(t)

    trips: list[dict[str, Any]] = []
    for sym in sorted(by_symbol):
        ordered = sorted(by_symbol[sym], key=lambda x: x.executed_at or datetime.min)
        long_q: deque[_Lot] = deque()
        short_q: deque[_Lot] = deque()

        for t in ordered:
            qty = max(0, int(t.quantity or 0))
            if qty <= 0:
                continue
            price = float(t.price or 0.0)
            fees = float(t.fees or 0.0)
            lot = _Lot(qty, price, fees, t.executed_at, t.id)
            remaining = qty
            fee_per = fees / qty if qty else 0.0

            if _side_is_buy(t.side):
                while remaining > 0 and short_q:
                    open_lot = short_q[0]
                    match = min(remaining, open_lot.qty)
                    pnl = (open_lot.price - price) * match
                    pnl -= fee_per * match + (open_lot.fees / open_lot.qty) * match
                    trips.append(
                        {
                            "symbol": sym,
                            "lane": trade_lane(sym),
                            "quantity": match,
                            "entry_price": price,
                            "exit_price": open_lot.price,
                            "realized_pnl": round(pnl, 2),
                            "closed_at": (t.executed_at or open_lot.executed_at).isoformat()
                            if (t.executed_at or open_lot.executed_at)
                            else None,
                            "direction": "short",
                        }
                    )
                    remaining -= match
                    open_lot.qty -= match
                    open_lot.fees -= fee_per * match
                    if open_lot.qty <= 0:
                        short_q.popleft()
                if remaining > 0:
                    long_q.append(
                        _Lot(remaining, price, fee_per * remaining, t.executed_at, t.id)
                    )
            else:
                while remaining > 0 and long_q:
                    open_lot = long_q[0]
                    match = min(remaining, open_lot.qty)
                    pnl = (price - open_lot.price) * match
                    pnl -= fee_per * match + (open_lot.fees / open_lot.qty) * match
                    trips.append(
                        {
                            "symbol": sym,
                            "lane": trade_lane(sym),
                            "quantity": match,
                            "entry_price": open_lot.price,
                            "exit_price": price,
                            "realized_pnl": round(pnl, 2),
                            "closed_at": (t.executed_at or open_lot.executed_at).isoformat()
                            if (t.executed_at or open_lot.executed_at)
                            else None,
                            "direction": "long",
                        }
                    )
                    remaining -= match
                    open_lot.qty -= match
                    open_lot.fees -= fee_per * match
                    if open_lot.qty <= 0:
                        long_q.popleft()
                if remaining > 0:
                    short_q.append(
                        _Lot(remaining, price, fee_per * remaining, t.executed_at, t.id)
                    )
    return trips


def fifo_stats(trades: list[Trade]) -> dict[str, Any]:
    trips = fifo_realized_trips(trades)
    pnls = [float(t["realized_pnl"]) for t in trips]
    wins = [p for p in pnls if p > 0]
    lanes = {"futures": 0, "cash": 0, "options": 0}
    lane_pnl = {"futures": 0.0, "cash": 0.0, "options": 0.0}
    for trip in trips:
        lane = trip.get("lane") or "cash"
        lanes[lane] = lanes.get(lane, 0) + 1
        lane_pnl[lane] = lane_pnl.get(lane, 0.0) + float(trip["realized_pnl"])

    return {
        "round_trips": len(trips),
        "net_pnl": round(sum(pnls), 2) if pnls else 0.0,
        "win_rate": round(len(wins) / len(pnls), 3) if pnls else None,
        "avg_trip_pnl": round(sum(pnls) / len(pnls), 2) if pnls else None,
        "lanes": lanes,
        "lane_pnl": {k: round(v, 2) for k, v in lane_pnl.items()},
    }
