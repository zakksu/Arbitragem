"""Clear cost model — B3 fees on 100-share stock scalps."""

from __future__ import annotations

from src.services.clear_cost_model import (
    breakeven_ticks,
    margin_stock_day_brl,
    round_trip_fees_brl,
    scalp_pnl_net_brl,
)
from src.services.paper_execution import estimate_paper_fills


def test_round_trip_fees_petr4():
    f = round_trip_fees_brl(price=38.0, quantity=100)
    assert f["notional_per_leg_brl"] == 3800.0
    assert f["b3_round_trip_brl"] > 0
    assert f["corretagem_brl"] == 0.0
    # 3800 * 0.00023 * 2 ≈ 1.75
    assert 1.5 < f["b3_round_trip_brl"] < 2.0


def test_breakeven_ticks_petr4():
    be = breakeven_ticks(price=38.0, quantity=100)
    assert be["tick_value_brl"] == 1.0  # R$0.01 × 100
    assert be["breakeven_ticks"] >= 2


def test_margin_50x():
    m = margin_stock_day_brl(price=38.0, quantity=100, leverage=50)
    assert m == 76.0  # 3800/50


def test_scalp_pnl_net():
    r = scalp_pnl_net_brl(price=38.0, exit_price=38.05, quantity=100, side="long")
    assert r["gross_brl"] == 5.0
    assert r["net_brl"] < r["gross_brl"]


def test_paper_fill_preview_includes_fees_per_leg():
    preview = estimate_paper_fills(
        {
            "symbol": "PETR4",
            "side": "long",
            "entry_price": 38.0,
            "legs": [
                {"symbol": "PETR4", "side": "buy", "quantity": 100},
                {"symbol": "PETR4", "side": "sell", "quantity": 100},
            ],
        }
    )
    assert preview["total_fees_brl"] > 0
    assert len(preview["legs"]) == 2
    for leg in preview["legs"]:
        assert leg["fees_brl"] > 0
        rt = round_trip_fees_brl(price=leg["expected_fill"], quantity=100)
        assert leg["fees_brl"] == rt["b3_fee_per_leg_brl"]
    assert preview["total_fees_brl"] == round(
        sum(l["fees_brl"] for l in preview["legs"]), 4
    )
