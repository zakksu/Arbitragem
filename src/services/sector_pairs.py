"""Sector basket correlation breaks — pair signals for scanner v2 (A2.5a)."""

from __future__ import annotations

from dataclasses import dataclass

from src.services.filipe_universe import SECTOR_BASKETS

# Baskets that emit relative-value pair ideas (energy + steel for 2.0-beta).
PAIR_BASKETS: dict[str, list[str]] = {
    "energy": SECTOR_BASKETS["energy"],
    "steel": SECTOR_BASKETS["steel"],
}


@dataclass
class SectorPairSignal:
    basket: str
    long_symbol: str
    short_symbol: str
    spread_pct: float
    reliability: float
    pattern_tags: list[str]

    def pair_label(self) -> str:
        return f"{self.long_symbol}/{self.short_symbol}"


def detect_sector_pairs(
    member_data: dict[str, dict],
    *,
    min_spread_pct: float = 0.35,
) -> list[SectorPairSignal]:
    """Detect mean-reversion pair setups when basket members diverge intraday."""
    signals: list[SectorPairSignal] = []

    for basket, symbols in PAIR_BASKETS.items():
        rows: list[tuple[str, float]] = []
        for sym in symbols:
            raw = member_data.get(sym.upper(), {})
            pct = raw.get("price_change_pct")
            if pct is None:
                continue
            rows.append((sym.upper(), float(pct)))

        if len(rows) < 2:
            continue

        leader = max(rows, key=lambda x: x[1])
        laggard = min(rows, key=lambda x: x[1])
        spread = round(leader[1] - laggard[1], 4)
        if spread < min_spread_pct:
            continue

        reliability = min(100.0, 35.0 + spread * 40.0)
        signals.append(
            SectorPairSignal(
                basket=basket,
                long_symbol=laggard[0],
                short_symbol=leader[0],
                spread_pct=spread,
                reliability=reliability,
                pattern_tags=["sector_corr_break", f"basket:{basket}", "pair_relative"],
            )
        )

    return signals
