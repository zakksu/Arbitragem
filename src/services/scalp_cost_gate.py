"""Breakeven gate for stock scalps — Clear B3 fees on 100-lot (12.0)."""

from __future__ import annotations

from typing import Any

from src.config import get_settings
from src.services.clear_cost_model import breakeven_ticks


def scalp_cost_gate(idea: dict[str, Any]) -> dict[str, Any]:
    """Return cost summary + whether target covers friction."""
    settings = get_settings()
    qty = int(settings.motor_fixed_lot_shares or 100)
    entry = float(idea.get("entry_price") or 0)
    target = float(idea.get("target_price") or 0)
    stop = float(idea.get("stop_price") or 0)
    side = str(idea.get("side") or "long").lower()

    if entry <= 0:
        return {"ok": True, "skipped": True, "reason": "no_entry_price"}

    be = breakeven_ticks(price=entry, quantity=qty)
    tick = 0.01 if entry < 50 else 0.05
    if side == "long":
        target_ticks = int(round((target - entry) / tick)) if target > entry else 0
    else:
        target_ticks = int(round((entry - target) / tick)) if target < entry else 0

    min_ticks = int(be["breakeven_ticks"])
    ok = target_ticks >= min_ticks
    leverage = float(settings.stock_day_leverage_assumed or 50.0)
    return {
        "ok": ok,
        "lot_shares": qty,
        "breakeven": be,
        "leverage": leverage,
        "target_ticks": target_ticks,
        "min_ticks_required": min_ticks,
        "entry": entry,
        "target": target,
        "stop": stop,
        "message": (
            None
            if ok
            else f"Target {target_ticks} ticks < breakeven {min_ticks} ticks (B3 fees ~R${be['b3_round_trip_brl']:.2f})"
        ),
    }
