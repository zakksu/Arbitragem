"""Opportunity rail — pair z-scores and sector heat (3.0-rc)."""

from __future__ import annotations

import hashlib

from src.integrations.profit_bridge import get_profit_client
from src.services.filipe_universe import SECTOR_BASKETS, load_filipe_core14


def _symbol_seed(symbol: str) -> int:
    return int(hashlib.md5(symbol.upper().encode()).hexdigest()[:8], 16)


def _zscore_stub(a_pct: float, b_pct: float, spread_hist: float = 0.5) -> float:
    spread = a_pct - b_pct
    return round(spread / max(spread_hist, 0.1), 2)


def build_opportunity_rail() -> dict:
    """PETR/PRIO energy pair + steel basket z-scores from live/stub quotes."""
    client = get_profit_client()
    core = {s.symbol: s for s in load_filipe_core14()}
    quotes: dict[str, float] = {}
    for sym in core:
        q = client.get_quote(sym)
        if q and q.last:
            seed = _symbol_seed(sym)
            quotes[sym] = round((seed % 200 - 100) / 100.0, 3)

    signals: list[dict] = []

    petr = quotes.get("PETR4", 0.0)
    prio = quotes.get("PRIO3", 0.0)
    energy_z = _zscore_stub(prio, petr)
    signals.append(
        {
            "id": "petr_prio",
            "label": "PETR / PRIO",
            "basket": "energy",
            "z_score": energy_z,
            "bias": "long_prio_short_petr" if energy_z > 1.0 else "long_petr_short_prio" if energy_z < -1.0 else "neutral",
            "symbols": ["PETR4", "PRIO3"],
        }
    )

    steel_syms = SECTOR_BASKETS.get("steel", ["GGBR4", "CSNA3", "USIM5"])
    steel_moves = [quotes.get(s, 0.0) for s in steel_syms if s in quotes]
    if len(steel_moves) >= 2:
        leader = max(steel_syms, key=lambda s: quotes.get(s, 0))
        laggard = min(steel_syms, key=lambda s: quotes.get(s, 0))
        steel_z = _zscore_stub(quotes.get(laggard, 0), quotes.get(leader, 0))
        signals.append(
            {
                "id": "steel_basket",
                "label": "Steel basket",
                "basket": "steel",
                "z_score": steel_z,
                "bias": f"long_{laggard}_short_{leader}" if abs(steel_z) > 0.8 else "neutral",
                "symbols": steel_syms,
            }
        )

    sector_heat: dict[str, float] = {}
    for basket, syms in SECTOR_BASKETS.items():
        vals = [quotes.get(s, 0) for s in syms if s in quotes]
        if vals:
            sector_heat[basket] = round(sum(vals) / len(vals), 3)

    return {
        "signals": signals,
        "sector_heat": sector_heat,
        "source": "stub" if not client.is_available() else "bridge",
    }
