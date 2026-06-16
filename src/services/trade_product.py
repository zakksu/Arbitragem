"""Trade Product schema builder — blended thesis/chart/legs card (4.0-beta)."""

from __future__ import annotations

from typing import Any

from src.services.idea_score import score_idea
from src.services.odds_panel import pattern_odds


def _clean_thesis(rationale: str | None, title: str | None) -> str:
    """Avoid kill-switch log spam in Trade Product thesis panel."""
    if title and (not rationale or "[Kill switch]" in rationale):
        return title
    if not rationale:
        return "Structure opportunity from scanner."
    first = rationale.strip().split("\n")[0]
    if "[Kill switch]" in first:
        return title or "Idea cancelled — run Scan for fresh setups."
    return first[:600]


def build_trade_product(
    idea: dict[str, Any], *, note: str | None = None, session=None
) -> dict[str, Any]:
    """Assemble Trade Product fields for blackboard API + template."""
    proof = idea.get("backtest_proof") or {}
    score = score_idea(idea)
    tags = idea.get("rationale_tags") or idea.get("tags") or []
    odds_extra = (
        pattern_odds(
            session,
            symbol=str(idea.get("symbol", "")),
            structure_type=idea.get("structure_type"),
        )
        if session is not None
        else {}
    )
    return {
        "symbol": idea.get("symbol"),
        "structure_type": idea.get("structure_type"),
        "side": idea.get("side"),
        "score": score,
        "thesis": _clean_thesis(idea.get("rationale"), idea.get("title")),
        "economics_tags": tags[:5],
        "why_not_alternatives": _alternatives(idea),
        "odds": {
            "win_rate_pct": odds_extra.get("win_rate_pct")
            or proof.get("win_rate_pct")
            or proof.get("win_rate"),
            "profit_factor": proof.get("profit_factor") or odds_extra.get("profit_factor"),
            "max_drawdown_pct": idea.get("dd_pct"),
            "sample_size": odds_extra.get("sample_size")
            or proof.get("trade_count")
            or proof.get("trades"),
            "source": odds_extra.get("source", "backtest_proof"),
        },
        "expected_gain_brl": _expected_gain(idea),
        "max_loss_brl": _max_loss(idea),
        "catalysts": [],
        "chart_levels": {
            "entry": idea.get("entry_price"),
            "stop": idea.get("stop_price"),
            "target": idea.get("target_price"),
        },
        "legs": idea.get("legs") or [],
        "ai_why": idea.get("rationale"),
        "notes": note,
    }


def _alternatives(idea: dict[str, Any]) -> list[str]:
    st = str(idea.get("structure_type", "scalp"))
    sym = idea.get("symbol", "")
    return [
        f"Cash {sym} — higher delta, no vol edge",
        f"Opposite structure — lower score in current regime",
        "Wait for VWAP reclaim — patience vs immediate entry",
    ]


def _expected_gain(idea: dict[str, Any]) -> float | None:
    entry = idea.get("entry_price")
    target = idea.get("target_price")
    if entry and target:
        return round(abs(float(target) - float(entry)) * 100, 2)
    return None


def _max_loss(idea: dict[str, Any]) -> float | None:
    entry = idea.get("entry_price")
    stop = idea.get("stop_price")
    if entry and stop:
        return round(abs(float(entry) - float(stop)) * 100, 2)
    return None
