"""Hardware-aware resource tuning for constrained hosts (<16 GB RAM).

Keeps the core quote/watchlist loop lean by centralizing TTLs and feature flags.
GPU offload is optional (Ollama external); probes CUDA only when torch is installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

if False:  # TYPE_CHECKING
    from src.config import Settings

LOW_RAM_BUDGET_CAP_MB = 500


@dataclass(frozen=True, slots=True)
class ResourceProfile:
    """Immutable runtime limits — avoids per-request dict churn."""

    low_ram: bool
    atr_cache_ttl_sec: float
    atr_cache_max_entries: int
    quote_cache_ttl_sec: float
    quote_cache_max_entries: int
    crypto_cache_ttl_sec: float
    watchlist_extra_universes: bool
    watchlist_ideas_limit: int
    autonomous_ideas_limit: int
    autonomous_strategy_limit: int
    scanner_universe_cache: bool
    sse_poll_sec: float
    effective_ram_budget_mb: int
    max_optimization_workers: int
    orchestrator_interval_sec: int
    streamlit_slim: bool
    background_tests: bool
    trader_desk_sse_sec: int
    scanner_ollama_on_scan: bool


def resolve_profile(*, low_ram: bool, settings: Any) -> ResourceProfile:
    """Map Settings + LOW_RAM_MODE into concrete limits."""
    if low_ram:
        budget = min(settings.ram_budget_mb, LOW_RAM_BUDGET_CAP_MB)
        return ResourceProfile(
            low_ram=True,
            atr_cache_ttl_sec=120.0,
            atr_cache_max_entries=16,
            quote_cache_ttl_sec=2.5,
            quote_cache_max_entries=2,
            crypto_cache_ttl_sec=10.0,
            watchlist_extra_universes=False,
            watchlist_ideas_limit=20,
            autonomous_ideas_limit=5,
            autonomous_strategy_limit=1,
            scanner_universe_cache=False,
            sse_poll_sec=4.0,
            effective_ram_budget_mb=budget,
            max_optimization_workers=1,
            orchestrator_interval_sec=settings.effective_orchestrator_interval_sec,
            streamlit_slim=True,
            background_tests=False,
            trader_desk_sse_sec=settings.desk_sse_interval_sec,
            scanner_ollama_on_scan=False,
        )
    return ResourceProfile(
        low_ram=False,
        atr_cache_ttl_sec=30.0,
        atr_cache_max_entries=64,
        quote_cache_ttl_sec=1.0,
        quote_cache_max_entries=8,
        crypto_cache_ttl_sec=5.0,
        watchlist_extra_universes=True,
        watchlist_ideas_limit=50,
        autonomous_ideas_limit=12,
        autonomous_strategy_limit=3,
        scanner_universe_cache=True,
        sse_poll_sec=2.0,
        effective_ram_budget_mb=settings.ram_budget_mb,
        max_optimization_workers=settings.optimization_max_workers,
        orchestrator_interval_sec=settings.orchestrator_interval_sec,
        streamlit_slim=settings.streamlit_slim_enabled,
        background_tests=settings.arbitragem_bg_tests,
        trader_desk_sse_sec=settings.desk_sse_interval_sec,
        scanner_ollama_on_scan=settings.scanner_ollama_on_scan,
    )


def get_resource_profile(settings: Any | None = None) -> ResourceProfile:
    from src.config import get_settings

    cfg = settings or get_settings()
    return resolve_profile(low_ram=cfg.low_ram_enabled, settings=cfg)


def profile_snapshot(settings: Any | None = None) -> dict[str, Any]:
    """JSON-safe summary for /ops/memory and status_tick."""
    prof = get_resource_profile(settings)
    return {
        "low_ram_mode": prof.low_ram,
        "effective_ram_budget_mb": prof.effective_ram_budget_mb,
        "atr_cache_ttl_sec": prof.atr_cache_ttl_sec,
        "atr_cache_max_entries": prof.atr_cache_max_entries,
        "quote_cache_ttl_sec": prof.quote_cache_ttl_sec,
        "quote_cache_max_entries": prof.quote_cache_max_entries,
        "watchlist_extra_universes": prof.watchlist_extra_universes,
        "watchlist_ideas_limit": prof.watchlist_ideas_limit,
        "sse_poll_sec": prof.sse_poll_sec,
        "max_optimization_workers": prof.max_optimization_workers,
        "orchestrator_interval_sec": prof.orchestrator_interval_sec,
        "background_tests": prof.background_tests,
        "compute": detect_compute_device(),
    }


def trim_timestamped_cache(cache: dict, max_entries: int) -> None:
    """Evict oldest entries from {key: (monotonic_ts, value)} caches."""
    while len(cache) > max_entries:
        oldest = min(cache.items(), key=lambda kv: kv[1][0])[0]
        cache.pop(oldest, None)


def detect_compute_device() -> dict[str, Any]:
    """Probe CUDA via PyTorch when installed; always safe CPU fallback."""
    try:
        import torch  # optional — not in base requirements

        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            return {
                "device": "cuda",
                "gpu_available": True,
                "name": props.name,
                "vram_total_mb": round(props.total_memory / (1024 * 1024), 1),
            }
    except ImportError:
        pass
    except Exception as exc:
        return {"device": "cpu", "gpu_available": False, "gpu_error": str(exc)[:120]}
    return {"device": "cpu", "gpu_available": False}
