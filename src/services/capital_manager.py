"""Motor capital sizing — risk-based quantity per idea/leg."""

from __future__ import annotations

from typing import Any

from src.config import get_settings
from src.integrations.profit_bridge import get_profit_client
from src.services.idea_levels import enrich_idea_levels


def _round_lot(qty: int, lot: int = 100) -> int:
    if qty <= 0:
        return lot
    return max(lot, (qty // lot) * lot)


def size_quantity_for_idea(idea: dict[str, Any], *, capital_brl: float | None = None) -> int:
    """
    Size cash leg quantity from motor capital and stop distance.

    risk_brl = capital × max_risk_per_trade_pct
    qty = risk_brl / |entry - stop|, capped by max_position_pct of capital.
    """
    settings = get_settings()
    capital = capital_brl if capital_brl is not None else settings.paper_capital_brl
    enriched = enrich_idea_levels(idea)
    entry = enriched.get("entry_price")
    stop = enriched.get("stop_price")
    if not entry or not stop:
        quote = get_profit_client().get_quote(str(idea.get("symbol", "")))
        entry = entry or (quote.last if quote else None)
    if not entry:
        return int(settings.default_max_contracts) * 100

    risk_budget = capital * (settings.max_risk_per_trade_pct / 100.0)
    per_share = abs(float(entry) - float(stop or entry))
    if per_share < 0.001:
        per_share = float(entry) * 0.005

    qty = int(risk_budget / per_share) if per_share else 100
    max_notional = capital * (settings.max_position_pct / 100.0)
    cap_qty = int(max_notional / float(entry)) if entry else qty
    qty = min(qty, cap_qty, settings.default_max_contracts * 100)
    return _round_lot(qty)


def apply_sizing_to_legs(idea: dict[str, Any]) -> list[dict[str, Any]]:
    """Return legs with motor-sized quantities for cash symbols."""
    legs_in = idea.get("legs") or [
        {"symbol": idea.get("symbol"), "side": "buy" if idea.get("side") == "long" else "sell", "quantity": 100}
    ]
    qty = size_quantity_for_idea(idea)
    out: list[dict[str, Any]] = []
    for leg in legs_in:
        leg = dict(leg)
        if leg.get("side") == "flat":
            out.append(leg)
            continue
        sym = str(leg.get("symbol", idea.get("symbol", "")))
        if leg.get("leg_type", "cash") in ("cash", None) or len(sym) <= 6:
            leg["quantity"] = qty
        out.append(leg)
    return out
