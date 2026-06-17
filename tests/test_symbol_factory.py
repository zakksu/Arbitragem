"""Symbol factory — shadow mode + promote gates (Release 7.0)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import PROJECT_ROOT, get_settings
from src.main import create_app
from src.models import get_session_factory, init_db
from src.services.symbol_factory import add_shadow_symbol, factory_status


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("BOARD_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    init_db()
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _clean_factory(monkeypatch):
    path = PROJECT_ROOT / "data" / "symbol_factory.json"
    if path.exists():
        path.unlink()
    yield
    if path.exists():
        path.unlink()


def test_factory_locked_without_green_sessions(monkeypatch):
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    get_settings.cache_clear()
    init_db()
    session = get_session_factory()()
    try:
        status = factory_status(session)
        assert status["locked"] is True
        assert "golden_path" in " ".join(status["lock_reasons"])
    finally:
        session.close()


def test_add_shadow_blocked_when_locked(monkeypatch):
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    get_settings.cache_clear()
    init_db()
    session = get_session_factory()()
    try:
        result = add_shadow_symbol(session, "PRIO3")
        assert result["ok"] is False
    finally:
        session.close()


def test_factory_status_api(client):
    r = client.get("/api/v1/symbol-factory/status")
    assert r.status_code == 200
    body = r.json()
    assert "locked" in body
    assert "candidates" in body
    assert body["golden_symbol"] == "PETR4"


def test_shadow_api_requires_symbol(client):
    r = client.post("/api/v1/symbol-factory/shadow", json={})
    assert r.status_code == 400


def test_symbol_factory_partial_200(client):
    r = client.get("/board/partials/symbol-factory")
    assert r.status_code == 200
    assert "bb-sf-panel" in r.text
    assert "Symbol Replication Factory" in r.text
    assert "PRIO3" in r.text or "Core14" in r.text


def test_board_shows_symbol_factory_button(client):
    r = client.get("/board")
    assert r.status_code == 200
    assert "symbol-factory" in r.text
