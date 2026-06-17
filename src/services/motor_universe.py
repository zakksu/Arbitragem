"""Core14 motor universe policy — concurrent symbols from RAM (10.0-GA)."""

from __future__ import annotations

from typing import Any

from src.config import get_settings
from src.services.filipe_universe import load_filipe_core14
from src.services.ops_panel import get_process_rss_mb
from src.services.resource_profile import get_resource_profile
from src.services.symbol_factory import factory_status


def motor_universe_policy(session) -> dict[str, Any]:
    settings = get_settings()
    prof = get_resource_profile()
    mem = get_process_rss_mb()
    rss = float(mem.get("rss_mb") or 0)
    budget = prof.effective_ram_budget_mb
    ram_frac = settings.resource_ram_fraction

    # ~200 MB per active motor symbol heuristic
    per_symbol_mb = 200
    headroom = budget * ram_frac
    max_auto = max(1, min(5, int(headroom / per_symbol_mb)))

    factory = factory_status(session)
    motor = [s.upper() for s in factory.get("motor_symbols", [])]
    shadow = [s["symbol"] for s in factory.get("shadow_symbols", factory.get("shadow", []))]
    core14 = [s.symbol.upper() for s in load_filipe_core14()]

    auto_active = motor[:max_auto]
    queued = [s for s in core14 if s not in auto_active and s not in shadow][:10]

    return {
        "max_concurrent_auto": max_auto,
        "auto_active": auto_active,
        "shadow": shadow,
        "queued": queued,
        "core14_count": len(core14),
        "rss_mb": rss,
        "budget_mb": budget,
        "ram_fraction": ram_frac,
    }
