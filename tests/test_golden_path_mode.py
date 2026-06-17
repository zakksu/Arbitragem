"""Golden path mode — PETR4-only watchlist when enabled."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.services.enriched_watchlist import build_enriched_watchlist
from src.web.router import _with_db


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("FUTURES_WATCHLIST_ENABLED", "true")
    monkeypatch.setenv("BOARD_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    return TestClient(create_app())


def test_scanner_universe_petr4_only(monkeypatch):
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    get_settings.cache_clear()
    assert get_settings().scanner_symbol_list == ["PETR4"]


def test_watchlist_sync_petr4_only(monkeypatch):
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    monkeypatch.setenv("FUTURES_WATCHLIST_ENABLED", "true")
    monkeypatch.setenv("CRYPTO_WATCHLIST_ENABLED", "true")
    get_settings.cache_clear()
    payload = _with_db(build_enriched_watchlist)
    symbols = [r["symbol"] for r in payload["symbols"]]
    assert symbols == ["PETR4"]


def test_watchlist_partial_petr4_only(client):
    r = client.get("/board/partials/watchlist")
    assert r.status_code == 200
    assert "PETR4" in r.text
    for sym in ("VALE3", "ITUB4", "BBDC4", "PRIO3"):
        assert sym not in r.text
