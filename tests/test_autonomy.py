"""Tests for autonomy engine."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import TradeIdea, get_session_factory, init_db
from src.services.trading_sleeves import set_all


@pytest.fixture
def client(monkeypatch):
    get_settings.cache_clear()
    set_all(True)
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("OLLAMA_ENABLED", "false")
    monkeypatch.setenv("AUTONOMY_ENABLED", "false")
    monkeypatch.setenv("AUTO_TRADING_ON_SLEEVES", "false")
    monkeypatch.setenv("PAPER_TRADING_MODE", "true")
    init_db()
    return TestClient(create_app())


def test_autonomy_status_disabled(client):
    r = client.get("/api/v1/autonomy/status")
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] is False


def test_autonomy_run_skipped_when_disabled(client):
    r = client.post("/api/v1/autonomy/run")
    assert r.status_code == 200
    assert r.json().get("skipped") in ("autonomy_disabled", "daily_trade_cap")


def test_autonomy_run_with_idea(client, monkeypatch):
    monkeypatch.setenv("AUTONOMY_ENABLED", "true")
    get_settings.cache_clear()
    init_db()

    session = get_session_factory()()
    idea = TradeIdea(
        symbol="PETR4",
        title="auto test",
        side="long",
        structure_type="scalp",
        legs=[{"symbol": "PETR4", "side": "buy", "quantity": 100, "leg_type": "cash"}],
        status="backtested",
        reliability=85,
        backtest_proof={"profit_factor": 1.6, "max_drawdown_pct": 4.0},
    )
    session.add(idea)
    session.commit()
    session.close()

    app = create_app()
    c = TestClient(app)
    r = c.post("/api/v1/autonomy/run")
    assert r.status_code == 200
    body = r.json()
    assert body.get("actions") or body.get("skipped")


def test_sleeves_api_get_post(client):
    r = client.get("/api/v1/risk/sleeves")
    assert r.status_code == 200
    assert "sleeves" in r.json()

    r2 = client.post("/api/v1/risk/sleeves", json={"sleeve": "cash", "open": False})
    assert r2.status_code == 200
    assert r2.json()["sleeves"]["cash"] is False

    client.post("/api/v1/risk/sleeves", json={"sleeve": "cash", "open": True})
