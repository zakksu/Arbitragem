"""Resource profile — low-RAM mode and compute device probe."""

from __future__ import annotations

import pytest

from src.config import get_settings
from src.services.enriched_watchlist import build_enriched_watchlist
from src.services.resource_profile import (
    detect_compute_device,
    get_resource_profile,
    profile_snapshot,
    resolve_profile,
)


@pytest.fixture
def low_ram_settings(monkeypatch):
    monkeypatch.setenv("LOW_RAM_MODE", "true")
    monkeypatch.setenv("CRYPTO_WATCHLIST_ENABLED", "true")
    monkeypatch.setenv("FUTURES_WATCHLIST_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_low_ram_profile_tightens_limits(low_ram_settings):
    prof = get_resource_profile()
    assert prof.low_ram is True
    assert prof.watchlist_extra_universes is False
    assert prof.atr_cache_ttl_sec >= 60
    assert prof.max_optimization_workers == 1
    assert prof.background_tests is False


def test_default_profile_allows_extra_universes(monkeypatch):
    monkeypatch.setenv("LOW_RAM_MODE", "false")
    get_settings.cache_clear()
    prof = get_resource_profile()
    assert prof.low_ram is False
    assert prof.watchlist_extra_universes is True


def test_enriched_watchlist_skips_crypto_in_low_ram(low_ram_settings, monkeypatch):
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    get_settings.cache_clear()
    from src.models import get_session_factory, init_db

    init_db()
    session = get_session_factory()()
    try:
        payload = build_enriched_watchlist(session)
    finally:
        session.close()
    symbols = {r["symbol"] for r in payload["symbols"]}
    assert "BTC" not in symbols
    assert payload["crypto_count"] == 0


def test_detect_compute_device_cpu_fallback():
    info = detect_compute_device()
    assert info["device"] in ("cpu", "cuda")
    assert "gpu_available" in info


def test_profile_snapshot_json_keys(low_ram_settings):
    snap = profile_snapshot()
    assert snap["low_ram_mode"] is True
    assert "quote_cache_ttl_sec" in snap
    assert "compute" in snap
