"""Shared pytest fixtures — fast, isolated test environment."""

from __future__ import annotations

import os

# Must run before Settings is first loaded.
os.environ["APP_ENV"] = "test"
os.environ["BOARD_AUTH_ENABLED"] = "false"
os.environ["DASHBOARD_AUTH_ENABLED"] = "false"
os.environ.setdefault("PROFIT_BRIDGE_ENABLED", "false")
os.environ.setdefault("PROFIT_BRIDGE_AUTO_DETECT", "false")
os.environ.setdefault("ENABLE_SCHEDULER", "false")
os.environ.setdefault("SCANNER_INCLUDE_BOVA_OPTIONS", "false")
os.environ.setdefault("OLLAMA_ENABLED", "false")
os.environ.setdefault("SCANNER_OLLAMA_ON_SCAN", "false")
os.environ.setdefault("JOURNAL_AUTO_ANALYZE", "false")
os.environ["EXECUTION_BACKEND"] = "paper"
os.environ["GOLDEN_PATH_MODE"] = "false"

import pytest

from src.config import get_settings


@pytest.fixture(autouse=True)
def _isolated_sqlite_db(monkeypatch, tmp_path_factory):
    """Fresh SQLite per test — avoids portfolio delta / P&L gate bleed across cases."""
    db_file = tmp_path_factory.mktemp("pytest_db") / "arbitragem.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_risk_profile():
    """Isolate risk profile row between tests."""
    from src.models import RiskProfile, get_session_factory, init_db

    init_db()
    session = get_session_factory()()
    try:
        session.query(RiskProfile).delete()
        session.commit()
    finally:
        session.close()
    yield


@pytest.fixture(autouse=True)
def _reset_trading_sleeves(monkeypatch, tmp_path_factory):
    """Isolate sleeve/kill-switch state — avoids data/trading_sleeves.json leaking between tests."""
    import src.services.trading_sleeves as ts

    path = tmp_path_factory.mktemp("sleeves") / "trading_sleeves.json"
    monkeypatch.setattr(ts, "_STATE_PATH", path)
    ts._state = {s: True for s in ts.SLEEVES}
    ts._paused_reason = ""
    ts._loaded = True
    yield
