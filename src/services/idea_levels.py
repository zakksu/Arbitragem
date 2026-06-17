"""Entry/stop/target enrichment and risk math for trade ideas."""

from __future__ import annotations

from typing import Any

from src.integrations.profit_bridge import get_profit_client


def enrich_idea_levels(idea: dict[str, Any]) -> dict[str, Any]:
    """Fill missing E/S/T from live quote when idea was created without prices."""
    out = dict(idea)
    entry = out.get("entry_price")
    side = str(out.get("side", "long")).lower()
    stop_t = int(out.get("stop_ticks") or 5)
    target_t = int(out.get("target_ticks") or 8)

    sym = str(out.get("symbol", "")).upper()
    if not entry and sym:
        quote = get_profit_client().get_quote(sym)
        if quote and quote.last:
            entry = float(quote.last)

    if entry:
        tick = 0.01 if entry < 50 else 0.05
        out["entry_price"] = round(float(entry), 4)
        if not out.get("stop_price"):
            if side == "long":
                out["stop_price"] = round(entry - stop_t * tick, 4)
            elif side == "short":
                out["stop_price"] = round(entry + stop_t * tick, 4)
        if not out.get("target_price"):
            if side == "long":
                out["target_price"] = round(entry + target_t * tick, 4)
            elif side == "short":
                out["target_price"] = round(entry - target_t * tick, 4)
    return out


def idea_risk_summary(idea: dict[str, Any], *, quantity: int = 100) -> dict[str, Any]:
    """Risk/reward in BRL for confirm modal."""
    enriched = enrich_idea_levels(idea)
    entry = enriched.get("entry_price")
    stop = enriched.get("stop_price")
    target = enriched.get("target_price")
    risk_brl = reward_brl = None
    rr = None
    if entry and stop:
        risk_brl = round(abs(float(entry) - float(stop)) * quantity, 2)
    if entry and target:
        reward_brl = round(abs(float(target) - float(entry)) * quantity, 2)
    if risk_brl and risk_brl > 0 and reward_brl is not None:
        rr = round(reward_brl / risk_brl, 2)
    return {
        "quantity": quantity,
        "risk_brl": risk_brl,
        "reward_brl": reward_brl,
        "risk_reward": rr,
        "entry_price": enriched.get("entry_price"),
        "stop_price": enriched.get("stop_price"),
        "target_price": enriched.get("target_price"),
    }
