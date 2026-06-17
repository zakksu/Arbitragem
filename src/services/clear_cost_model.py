"""Clear / B3 cost model for stock scalps — 100-share lots (12.0).

Rates from Clear custos operacionais (day trade ações):
  emolumentos 0.005% + liquidação 0.018% per leg.
Corretagem R$0 on electronic + RLP.

Crypto live: intentionally NOT modeled — Binance integration is read-only quotes;
no broker margin/fee contract in repo. See RELEASE_12.0.0.md.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT

_COSTS_PATH = PROJECT_ROOT / "data" / "clear_costs.json"


@lru_cache
def load_clear_costs() -> dict[str, Any]:
    if not _COSTS_PATH.exists():
        return {
            "day_trade_stocks": {
                "emolumentos_pct": 0.00005,
                "liquidacao_pct": 0.00018,
                "total_b3_pct_per_leg": 0.00023,
            },
            "default_lot_shares": 100,
        }
    return json.loads(_COSTS_PATH.read_text(encoding="utf-8"))


def b3_fee_per_leg(notional_brl: float) -> float:
    """B3 emolumentos + liquidação for one leg (buy or sell)."""
    rates = load_clear_costs().get("day_trade_stocks", {})
    pct = float(rates.get("total_b3_pct_per_leg", 0.00023))
    return round(notional_brl * pct, 4)


def round_trip_fees_brl(*, price: float, quantity: int = 100) -> dict[str, Any]:
    """Full round-trip B3 fees for a stock scalp (buy + sell)."""
    qty = int(quantity)
    notional = float(price) * qty
    per_leg = b3_fee_per_leg(notional)
    total = round(per_leg * 2, 4)
    return {
        "quantity": qty,
        "price": price,
        "notional_per_leg_brl": round(notional, 2),
        "b3_fee_per_leg_brl": per_leg,
        "b3_round_trip_brl": total,
        "corretagem_brl": 0.0,
    }


def slippage_estimate_brl(*, price: float, quantity: int = 100, ticks: int = 1) -> float:
    """1 tick per side default — PETR4 tick R$0.01/share."""
    tick = 0.01 if price < 50 else 0.05
    return round(tick * quantity * ticks * 2, 4)  # buy + sell


def breakeven_ticks(*, price: float, quantity: int = 100) -> dict[str, Any]:
    """Ticks needed to cover B3 fees + 1-tick slippage each side."""
    fees = round_trip_fees_brl(price=price, quantity=quantity)
    slip = slippage_estimate_brl(price=price, quantity=quantity, ticks=1)
    friction = fees["b3_round_trip_brl"] + slip
    tick_value = (0.01 if price < 50 else 0.05) * quantity
    ticks_needed = max(1, int(friction / tick_value) + (1 if friction % tick_value else 0))
    return {
        **fees,
        "slippage_1tick_each_side_brl": slip,
        "total_friction_brl": round(friction, 4),
        "tick_value_brl": tick_value,
        "breakeven_ticks": ticks_needed,
        "breakeven_price_move_brl": round(ticks_needed * (0.01 if price < 50 else 0.05), 4),
    }


def margin_stock_day_brl(*, price: float, quantity: int = 100, leverage: float = 50.0) -> float:
    """Pré-margem estimate: notional / leverage (Clear advertises up to 200x)."""
    notional = float(price) * int(quantity)
    lev = max(1.0, float(leverage))
    return round(notional / lev, 2)


def scalp_pnl_net_brl(
    *,
    price: float,
    exit_price: float,
    quantity: int = 100,
    side: str = "long",
) -> dict[str, Any]:
    """Gross P&L minus B3 round-trip fees (no IR)."""
    qty = int(quantity)
    if side.lower() in ("long", "buy"):
        gross = (float(exit_price) - float(price)) * qty
    else:
        gross = (float(price) - float(exit_price)) * qty
    fees = round_trip_fees_brl(price=price, quantity=qty)
    net = round(gross - fees["b3_round_trip_brl"], 2)
    return {"gross_brl": round(gross, 2), "fees_brl": fees["b3_round_trip_brl"], "net_brl": net}


def cost_summary_for_symbol(symbol: str, price: float, *, quantity: int = 100, leverage: float = 50.0) -> dict[str, Any]:
    """Board / confirm modal payload."""
    be = breakeven_ticks(price=price, quantity=quantity)
    margin = margin_stock_day_brl(price=price, quantity=quantity, leverage=leverage)
    return {
        "symbol": symbol.upper(),
        "lot_shares": quantity,
        "leverage_assumed": leverage,
        "margin_estimate_brl": margin,
        "breakeven": be,
        "source": "clear_cost_model",
    }
