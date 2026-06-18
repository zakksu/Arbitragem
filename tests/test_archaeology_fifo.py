"""FIFO archaeology P&L + futures roll tests."""

from __future__ import annotations

from datetime import datetime

from src.models import Trade
from src.services.archaeology_fifo import fifo_realized_trips, fifo_stats, trade_lane
from src.services.futures_roll import resolve_front_contract, resolve_futures_quote_symbol


def test_trade_lane():
    assert trade_lane("PETR4") == "cash"
    assert trade_lane("WINJ26") == "futures"
    assert trade_lane("PETRA230") == "options"


def test_fifo_round_trip_petr4():
    t1 = Trade(
        external_id="t1",
        source="archaeology",
        symbol="PETR4",
        side="buy",
        quantity=100,
        price=38.20,
        executed_at=datetime(2025, 11, 13, 10, 0),
    )
    t2 = Trade(
        external_id="t2",
        source="archaeology",
        symbol="PETR4",
        side="sell",
        quantity=100,
        price=38.50,
        executed_at=datetime(2025, 11, 13, 11, 0),
    )
    trips = fifo_realized_trips([t1, t2])
    assert len(trips) == 1
    assert trips[0]["realized_pnl"] == 30.0
    stats = fifo_stats([t1, t2])
    assert stats["round_trips"] == 1
    assert stats["net_pnl"] == 30.0


def test_win_front_month_resolver():
    sym = resolve_front_contract("WIN", ref=datetime(2026, 6, 10).date())
    assert sym.startswith("WIN")
    assert len(sym) >= 6
    meta = resolve_futures_quote_symbol("WINFUT")
    assert meta["resolved"].startswith("WIN")
