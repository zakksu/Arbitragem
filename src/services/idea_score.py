"""Idea score 0–100 — reliability × gates × WF × vol fit × cost/spread penalties."""

from __future__ import annotations

from typing import Any

from src.services.filipe_universe import sector_for


def _sector_from_tags(tags: list[str]) -> str | None:
    for t in tags:
        if str(t).startswith("sector:"):
            return str(t).split(":", 1)[1].lower()
    return None


def score_idea(
    idea: dict[str, Any],
    *,
    gate_ok: bool = True,
    open_stack: list[dict[str, Any]] | None = None,
    est_cost_brl: float | None = None,
    spread_pct: float | None = None,
) -> int:
    """
    Compute ranked score for watchlist and idea stack.

    Base: reliability × gate × WF × PF × vol-fit multipliers.
    Penalties:
      - est_cost_brl / notional > 0.5% → up to −12 pts
      - spread_pct > 0.15% → up to −10 pts
      - >2 open ideas same sector → −8 pts per extra
      - backtest DD > 15% → −15 pts
    Bonuses:
      - walk_forward_pass → ×1.12 (already in wf_mult)
    """
    reliability = float(idea.get("reliability", 0) or 0)
    proof = idea.get("backtest_proof") or {}
    pf = float(proof.get("profit_factor", 1.0) or 1.0)
    wf_pass = bool(idea.get("walk_forward_pass"))
    status = str(idea.get("status", "detected"))
    tags = idea.get("rationale_tags") or idea.get("tags") or []

    gate_mult = 1.0 if gate_ok else 0.55
    if status in ("confirmed", "executed"):
        gate_mult *= 0.85
    wf_mult = 1.12 if wf_pass else 0.92
    pf_mult = min(1.25, max(0.65, pf / 1.4))

    vol_fit = 1.0
    if any(t in tags for t in ("vwap_reclaim", "mean_reversion", "sector_pair")):
        vol_fit = 1.08

    raw = reliability * gate_mult * wf_mult * pf_mult * vol_fit
    score = max(0, min(100, int(round(raw))))

    dd = proof.get("max_drawdown_pct")
    if dd is not None:
        try:
            if abs(float(dd)) > 15.0:
                score = max(0, score - 15)
        except (TypeError, ValueError):
            pass

    entry = idea.get("entry_price")
    notional = float(entry) * 100.0 if entry else 0.0
    cost = est_cost_brl
    if cost is None:
        cost = float(idea.get("est_cost_brl") or 0)
    if notional > 0 and cost > 0:
        cost_ratio = cost / notional
        if cost_ratio > 0.005:
            score = max(0, score - min(12, int(cost_ratio * 1000)))

    if spread_pct is None and entry and idea.get("bid") and idea.get("ask"):
        mid = (float(idea["bid"]) + float(idea["ask"])) / 2.0
        if mid > 0:
            spread_pct = (float(idea["ask"]) - float(idea["bid"])) / mid * 100.0
    if spread_pct is not None and spread_pct > 0.15:
        score = max(0, score - min(10, int(spread_pct / 0.15 * 5)))

    if open_stack:
        sym = str(idea.get("symbol", "")).upper()
        sector = _sector_from_tags(tags) or (sector_for(sym) or "").lower()
        if sector:
            same = 0
            for other in open_stack:
                if other.get("id") == idea.get("id"):
                    continue
                if str(other.get("status", "")) in ("rejected", "executed"):
                    continue
                otags = other.get("rationale_tags") or other.get("tags") or []
                osec = _sector_from_tags(otags) or (
                    sector_for(str(other.get("symbol", ""))) or ""
                ).lower()
                if osec == sector:
                    same += 1
            if same > 2:
                score = max(0, score - (same - 2) * 8)

    return score


def top_score_by_symbol(
    ideas: list[dict[str, Any]],
    *,
    open_stack: list[dict[str, Any]] | None = None,
) -> dict[str, int]:
    """Best idea score per symbol."""
    stack = open_stack if open_stack is not None else ideas
    best: dict[str, int] = {}
    for idea in ideas:
        sym = str(idea.get("symbol", "")).upper()
        if not sym:
            continue
        s = score_idea(idea, open_stack=stack)
        best[sym] = max(best.get(sym, 0), s)
    return best
