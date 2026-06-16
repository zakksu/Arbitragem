"""Idea score 0–100 — reliability × gate × WF × vol fit (4.0-alpha)."""

from __future__ import annotations

from typing import Any


def score_idea(idea: dict[str, Any], *, gate_ok: bool = True) -> int:
    """Compute ranked score for watchlist and idea stack."""
    reliability = float(idea.get("reliability", 0) or 0)
    proof = idea.get("backtest_proof") or {}
    pf = float(proof.get("profit_factor", 1.0) or 1.0)
    wf_pass = bool(idea.get("walk_forward_pass"))
    status = str(idea.get("status", "detected"))

    gate_mult = 1.0 if gate_ok else 0.55
    if status in ("confirmed", "executed"):
        gate_mult *= 0.85
    wf_mult = 1.12 if wf_pass else 0.92
    pf_mult = min(1.25, max(0.65, pf / 1.4))

    vol_fit = 1.0
    tags = idea.get("rationale_tags") or idea.get("tags") or []
    if any(t in tags for t in ("vwap_reclaim", "mean_reversion", "sector_pair")):
        vol_fit = 1.08

    raw = reliability * gate_mult * wf_mult * pf_mult * vol_fit
    return max(0, min(100, int(round(raw))))


def top_score_by_symbol(ideas: list[dict[str, Any]]) -> dict[str, int]:
    """Best idea score per symbol."""
    best: dict[str, int] = {}
    for idea in ideas:
        sym = str(idea.get("symbol", "")).upper()
        if not sym:
            continue
        s = score_idea(idea)
        best[sym] = max(best.get(sym, 0), s)
    return best
