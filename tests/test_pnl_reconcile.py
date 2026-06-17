"""P&L reconciliation — PETR4 journal vs Profit (Release 7.0)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import get_session_factory, init_db
from src.services.pnl_reconcile import last_reconcile, reconcile_symbol_pnl


@pytest.fixture(autouse=True)
def _db(monkeypatch):
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("BOARD_AUTH_ENABLED", "false")
    init_db()
    yield


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("BOARD_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    return TestClient(create_app())


def test_reconcile_structure():
    session = get_session_factory()()
    try:
        data = reconcile_symbol_pnl(session, "PETR4")
        assert data["symbol"] == "PETR4"
        assert "within_tolerance" in data
        assert "diff_pct" in data
        assert data["within_tolerance"] is True
    finally:
        session.close()


def test_last_reconcile_cached():
    session = get_session_factory()()
    try:
        first = reconcile_symbol_pnl(session, "PETR4")
        second = last_reconcile()
        assert second["symbol"] == first["symbol"]
        assert second["diff_pct"] == first["diff_pct"]
    finally:
        session.close()


def test_reconcile_api(client):
    r = client.get("/api/v1/golden-path/reconcile")
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "PETR4"
