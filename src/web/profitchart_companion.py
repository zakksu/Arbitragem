"""ProfitChart Companion — side-by-side level overlays for external chart (10.0 UI)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.config import get_settings
from src.integrations.profit_bridge import get_profit_client


def build_profitchart_companion(
    symbol: str,
    *,
    quote: dict[str, Any] | None = None,
    top_idea: dict[str, Any] | None = None,
    session_vwap: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    sym = symbol.strip().upper()
    last = None
    if quote and quote.get("last") is not None:
        last = float(quote["last"])

    levels: list[dict[str, Any]] = []
    if top_idea:
        for key, label, color in (
            ("entry", "Entry", "#f59e0b"),
            ("stop", "Stop", "#ef4444"),
            ("target", "Target", "#22c55e"),
        ):
            val = top_idea.get(key)
            if val is not None:
                try:
                    price = float(val)
                except (TypeError, ValueError):
                    continue
                dist = abs(price - last) / last * 100 if last and last > 0 else None
                levels.append(
                    {
                        "id": key,
                        "label": label,
                        "price": price,
                        "color": color,
                        "dist_pct": round(dist, 2) if dist is not None else None,
                    }
                )

    vwap = None
    if session_vwap and session_vwap.get("session_vwap") is not None:
        vwap = float(session_vwap["session_vwap"])
        dist = session_vwap.get("vwap_distance_pct")
        levels.append(
            {
                "id": "vwap",
                "label": "Session VWAP",
                "price": vwap,
                "color": "#8b5cf6",
                "dist_pct": round(float(dist), 2) if dist is not None else None,
            }
        )

    exe = settings.profitchart_exe.strip()
    exe_ok = bool(exe and Path(exe).exists())
    bridge = get_profit_client().is_available()

    return {
        "symbol": sym,
        "last": last,
        "levels": levels,
        "profitchart_exe": exe if exe_ok else None,
        "profitchart_co_start": settings.profitchart_co_start,
        "bridge_online": bridge,
        "companion_mode": True,
        "hint": "Mirror these levels in ProfitChart — board stays in sync via bridge quotes.",
    }
