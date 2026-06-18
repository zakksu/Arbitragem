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


SCALP_STRUCTURE_IDS: frozenset[str] = frozenset(
    {
        StructureType.SCALP.value,
        "scalp_long",
        "scalp_short",
        "stock_scalp_vwap",
        "opening_range_break",
        "mean_reversion_band",
        "archaeology_bias_long",
        "pulse_scalp",
    }
)

PAPER_MOTOR_STRUCTURES: tuple[str, ...] = (
    "stock_scalp_vwap",
    "pulse_scalp",
    "opening_range_break",
    "mean_reversion_band",
    "archaeology_bias_long",
)

FUTURES_MOTOR_STRUCTURES: tuple[str, ...] = (
    "futures_open_drive",
    "futures_vwap_reclaim",
    "futures_lunch_fade",
    "futures_afternoon_trend",
    "futures_failed_breakout",
)

STRUCTURE_TO_REPLAY_STRATEGY: dict[str, str] = {
    "stock_scalp_vwap": "s1_vwap_reclaim",
    "opening_range_break": "s2_orb_break",
    "mean_reversion_band": "s3_bb_fade",
    "archaeology_bias_long": "s4_arch_bias",
    "pulse_scalp": "s5_pulse",
    "futures_open_drive": "f1_open_drive",
    "futures_vwap_reclaim": "f2_vwap_reclaim",
    "futures_lunch_fade": "f3_lunch_fade",
    "futures_afternoon_trend": "f4_afternoon_trend",
    "futures_failed_breakout": "f5_failed_breakout",
    "scalp_long": "s1_vwap_reclaim",
    "scalp_short": "scalp_short",
    "scalp": "scalp_default",
}

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
    {
        "id": "futures_open_drive",
        "label": "Open drive (F1)",
        "legs_min": 1,
        "description": "WIN/WDO first-hour momentum",
    },
    {
        "id": "futures_vwap_reclaim",
        "label": "Futures VWAP (F2)",
        "legs_min": 1,
        "description": "Front-month reclaim of session VWAP",
    },
    {
        "id": "futures_lunch_fade",
        "label": "Lunch fade (F3)",
        "legs_min": 1,
        "description": "Mean reversion into lunch lull",
    },
    {
        "id": "futures_afternoon_trend",
        "label": "Afternoon trend (F4)",
        "legs_min": 1,
        "description": "13:00–17:00 continuation",
    },
    {
        "id": "futures_failed_breakout",
        "label": "Failed breakout (F5)",
        "legs_min": 1,
        "description": "Fade false range extension",
    },
]


def is_cash_scalp(structure: str) -> bool:
    return structure.lower() in SCALP_STRUCTURE_IDS


def replay_strategy_for_structure(structure: str) -> str:
    return STRUCTURE_TO_REPLAY_STRATEGY.get(structure.lower(), "scalp_default")


def enabled_structure_types(enabled_csv: str) -> list[dict]:
    allowed = {s.strip() for s in enabled_csv.split(",") if s.strip()}
    if not allowed:
        return list(STRUCTURE_CATALOG)
    return [row for row in STRUCTURE_CATALOG if row["id"] in allowed]
