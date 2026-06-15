"""Scanner v3 structure signals — max pain, IV context (stub-friendly)."""

from __future__ import annotations

from typing import Any


def compute_max_pain(chain: dict[str, Any]) -> dict[str, Any] | None:
    """Max pain strike from call/put open interest in an option chain."""
    calls = chain.get("calls") or []
    puts = chain.get("puts") or []
    if not calls and not puts:
        return None

    strikes: set[float] = set()
    for leg in calls + puts:
        strike = leg.get("strike")
        if strike is not None:
            strikes.add(float(strike))
    if not strikes:
        return None

    underlying_last = float(chain.get("underlying_last") or 0)
    pain_by_strike: dict[float, float] = {}

    for test_strike in sorted(strikes):
        total_pain = 0.0
        for call in calls:
            strike = float(call.get("strike", 0))
            oi = float(call.get("open_interest") or call.get("volume") or 0)
            if test_strike > strike:
                total_pain += (test_strike - strike) * oi
        for put in puts:
            strike = float(put.get("strike", 0))
            oi = float(put.get("open_interest") or put.get("volume") or 0)
            if test_strike < strike:
                total_pain += (strike - test_strike) * oi
        pain_by_strike[test_strike] = total_pain

    max_pain_strike = min(pain_by_strike, key=pain_by_strike.get)  # type: ignore[arg-type]
    distance_pct = None
    if underlying_last > 0:
        distance_pct = round((underlying_last - max_pain_strike) / underlying_last * 100, 3)

    return {
        "underlying": chain.get("underlying"),
        "max_pain_strike": max_pain_strike,
        "underlying_last": underlying_last,
        "distance_pct": distance_pct,
        "total_oi_calls": sum(int(c.get("open_interest") or c.get("volume") or 0) for c in calls),
        "total_oi_puts": sum(int(p.get("open_interest") or p.get("volume") or 0) for p in puts),
        "source": chain.get("source", "chain"),
    }


def max_pain_tags(signal: dict[str, Any] | None) -> list[str]:
    """Rationale tags when price is near max pain."""
    if not signal:
        return []
    tags = ["max_pain"]
    dist = signal.get("distance_pct")
    if dist is not None and abs(float(dist)) <= 1.5:
        tags.append("near_max_pain")
    return tags
