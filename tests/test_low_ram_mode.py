"""Low-RAM mode — config helpers and runtime toggles (Release 7.0)."""

from __future__ import annotations

import pytest

from src.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_low_ram_explicit_env(monkeypatch):
    monkeypatch.setenv("LOW_RAM_MODE", "true")
    monkeypatch.setenv("GOLDEN_PATH_MODE", "false")
    s = get_settings()
    assert s.low_ram_enabled is True
    assert s.ollama_runtime_enabled is False
    assert s.social_signals_runtime_enabled is False
    assert s.streamlit_slim_enabled is True
    assert s.desk_sse_interval_sec == 60
    assert s.quotes_heartbeat_sec == 30
    assert s.trader_desk_journal_limit == 15
    assert s.streamlit_cache_ttl_sec == 30


def test_golden_path_auto_enables_low_ram(monkeypatch):
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    monkeypatch.setenv("LOW_RAM_MODE", "false")
    s = get_settings()
    assert s.low_ram_enabled is True
    assert s.scanner_symbol_list == ["PETR4"]
    assert s.desk_sse_interval_sec == 60
    assert s.effective_paper_orchestrator_interval_sec == 30


def test_motor_interval_plus_fifty_percent(monkeypatch):
    monkeypatch.setenv("LOW_RAM_MODE", "true")
    monkeypatch.setenv("PAPER_ORCHESTRATOR_INTERVAL_SEC", "20")
    monkeypatch.setenv("ORCHESTRATOR_INTERVAL_SEC", "40")
    s = get_settings()
    assert s.effective_paper_orchestrator_interval_sec == 30
    assert s.effective_orchestrator_interval_sec == 60


def test_default_mode_unchanged(monkeypatch):
    monkeypatch.setenv("LOW_RAM_MODE", "false")
    monkeypatch.setenv("GOLDEN_PATH_MODE", "false")
    monkeypatch.setenv("OLLAMA_ENABLED", "true")
    get_settings.cache_clear()
    s = get_settings()
    assert s.low_ram_enabled is False
    assert s.ollama_runtime_enabled is True
    assert s.desk_sse_interval_sec == 10
    assert s.trader_desk_journal_limit == 35


def test_resource_profile_follows_low_ram(monkeypatch):
    monkeypatch.setenv("LOW_RAM_MODE", "true")
    from src.services.resource_profile import get_resource_profile

    prof = get_resource_profile()
    assert prof.low_ram is True
    assert prof.watchlist_extra_universes is False
    assert prof.trader_desk_sse_sec == 60
