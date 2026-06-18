"""3.0 structure deck — leg types, templates, and metadata."""

from __future__ import annotations

from enum import Enum


class StructureType(str, Enum):
    SCALP = "scalp"
    COVERED_CALL = "covered_call"
    VERTICAL = "vertical"
    COLLAR = "collar"
    BOVA_HEDGE = "bova_hedge"
    PAIR_SPREAD = "pair_spread"


class LegType(str, Enum):
    CASH = "cash"
    CALL = "call"
    PUT = "put"
    BOVA_CALL = "bova_call"
    BOVA_PUT = "bova_put"


STRUCTURE_CATALOG: list[dict] = [
    {
        "id": StructureType.SCALP.value,
        "label": "Scalp",
        "legs_min": 1,
        "description": "Single-symbol cash intraday scalp",
    },
    {
        "id": StructureType.COVERED_CALL.value,
        "label": "Covered call",
        "legs_min": 2,
        "description": "Long stock + short OTM call",
    },
    {
        "id": StructureType.VERTICAL.value,
        "label": "Vertical spread",
        "legs_min": 2,
        "description": "Bull/bear call or put spread on Core14",
    },
    {
        "id": StructureType.COLLAR.value,
        "label": "Collar",
        "legs_min": 3,
        "description": "Long stock + protective put + short call",
    },
    {
        "id": StructureType.BOVA_HEDGE.value,
        "label": "BOVA hedge",
        "legs_min": 2,
        "description": "Core14 basket exposure + BOVA index option hedge",
    },
    {
        "id": StructureType.PAIR_SPREAD.value,
        "label": "Pair spread",
        "legs_min": 2,
        "description": "Sector pair relative value (cash legs)",
    },
    {
        "id": "stock_scalp_vwap",
        "label": "VWAP reclaim (S1)",
        "legs_min": 1,
        "description": "Close back above session VWAP — 4 tick stop, 6 tick target",
    },
    {
        "id": "opening_range_break",
        "label": "Opening range (S2)",
        "legs_min": 1,
        "description": "15m high/low break 10:00–12:00",
    },
    {
        "id": "mean_reversion_band",
        "label": "Mean reversion (S3)",
        "legs_min": 1,
        "description": "Lower band touch + RSI oversold, target VWAP",
    },
    {
        "id": "archaeology_bias_long",
        "label": "Archaeology bias (S4)",
        "legs_min": 1,
        "description": "Long when your B3 history net flow is green",
    },
    {
        "id": "pulse_scalp",
        "label": "Pulse scalp (S5)",
        "legs_min": 1,
        "description": "Live Radar all green + CASH sleeve — max 3/day",
    },
]


def enabled_structure_types(enabled_csv: str) -> list[dict]:
    allowed = {s.strip() for s in enabled_csv.split(",") if s.strip()}
    if not allowed:
        return list(STRUCTURE_CATALOG)
    return [row for row in STRUCTURE_CATALOG if row["id"] in allowed]
