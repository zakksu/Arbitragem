"""Scanner tests — IBOV top 20 mode."""

import pytest

from src.config import get_settings
from src.models import get_session_factory, init_db
from src.services.scanner import PatternScanner


@pytest.fixture
def db_session():
    get_settings.cache_clear()
    init_db()
    session = get_session_factory()()
    yield session
    session.close()


def test_scan_ibov_top20(db_session, monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("SCANNER_MODE", "ibov_top20")
    monkeypatch.setenv("SCANNER_INCLUDE_BOVA_OPTIONS", "false")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")

    class FakeOllama:
        def is_available(self):
            return False

    monkeypatch.setattr("src.services.scanner.get_ollama_client", lambda: FakeOllama())

    results = PatternScanner(db_session).run_daily_scan()
    assert len(results) == 20
    assert results[0].raw_data is not None
    assert "reliability" in results[0].raw_data
    assert "side_bias" in results[0].raw_data


def test_scalp_insights(db_session, monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("SCANNER_MODE", "ibov_top20")
    monkeypatch.setenv("SCANNER_INCLUDE_BOVA_OPTIONS", "false")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")

    class FakeOllama:
        def is_available(self):
            return False

    monkeypatch.setattr("src.services.scanner.get_ollama_client", lambda: FakeOllama())

    scanner = PatternScanner(db_session)
    scanner.run_daily_scan()
    insights = scanner.get_scalp_insights(limit=5)
    assert len(insights) <= 5
    if insights:
        assert "symbol" in insights[0]
        assert "reliability" in insights[0]
