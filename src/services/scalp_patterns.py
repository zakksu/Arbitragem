"""Scalping pattern detection for IBOV intraday tape (seconds to minutes)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScalpSignal:
    reliability: float
    side_bias: str  # long | short | neutral
    pattern_tags: list[str]
    stop_ticks: int
    target_ticks: int

    def to_dict(self) -> dict:
        return {
            "reliability": round(self.reliability, 1),
            "side_bias": self.side_bias,
            "pattern_tags": self.pattern_tags,
            "stop_ticks": self.stop_ticks,
            "target_ticks": self.target_ticks,
        }


def analyze_scalp(
    *,
    volume: int,
    spike_score: float,
    price_change_pct: float | None,
    spread: float | None,
    min_volume: int,
    avg_volume_30d: int | None = None,
    vwap_reclaim_long: bool = False,
    vwap_reclaim_short: bool = False,
) -> ScalpSignal:
    tags: list[str] = []
    score = 0.0
    side = "neutral"
    baseline = max(avg_volume_30d or 1, min_volume)
    vol_ratio = volume / baseline

    if volume >= min_volume:
        tags.append("high_volume")
        score += 10 + min(15, vol_ratio * 400)

    if spike_score >= 35:
        tags.append("volume_spike")
        score += min(25, spike_score * 0.35)

    if vol_ratio >= 0.008:
        tags.append("momentum_burst")
        score += min(20, vol_ratio * 600)

    if price_change_pct is not None:
        if price_change_pct > 0.25:
            tags.append("scalp_long")
            side = "long"
            score += min(25, abs(price_change_pct) * 12)
        elif price_change_pct < -0.25:
            tags.append("scalp_short")
            side = "short"
            score += min(25, abs(price_change_pct) * 12)
        if abs(price_change_pct) > 0.8:
            tags.append("price_spike")
            score += 10

    if spread is not None and spread > 0:
        mid = max(spread * 80, 0.05)
        if spread / mid < 0.003:
            tags.append("spread_compression")
            score += 12

    if vwap_reclaim_long:
        tags.append("vwap_reclaim")
        if side == "neutral":
            side = "long"
        score += 14
    elif vwap_reclaim_short:
        tags.append("vwap_reject")
        if side == "neutral":
            side = "short"
        score += 12

    if spike_score > 55 and price_change_pct is not None and not vwap_reclaim_long:
        if price_change_pct > 0.1:
            tags.append("vwap_reclaim")
            if side == "neutral":
                side = "long"
            score += 8
        elif price_change_pct < -0.1:
            if side == "neutral":
                side = "short"
            score += 8

    reliability = min(100.0, score)
    if reliability < 20 and spike_score > 0:
        reliability = max(reliability, min(40.0, spike_score * 0.45))

    stop = 3 if reliability > 75 else 4 if reliability > 55 else 5
    target = 10 if side != "neutral" and reliability > 60 else 8 if side != "neutral" else 6

    return ScalpSignal(
        reliability=reliability,
        side_bias=side,
        pattern_tags=tags,
        stop_ticks=stop,
        target_ticks=target,
    )
