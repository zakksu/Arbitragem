"""Board notes and backtest gate tests (2.0)."""

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import init_db
from src.services.trade_ideas import TradeIdeaService


@pytest.fixture
def client(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("SCANNER_OLLAMA_ON_SCAN", "false")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    init_db()
    return TestClient(create_app())


def test_board_notes_roundtrip(client):
    r = client.put("/api/v1/board/PETR4/notes", json={"content": "Support 38.20"})
    assert r.status_code == 200
    data = r.json()
    assert data["symbol"] == "PETR4"
    assert "38.20" in data["content"]

    r2 = client.get("/api/v1/board/PETR4/notes")
    assert r2.status_code == 200
    assert r2.json()["content"] == data["content"]


def test_backtest_gate():
    assert TradeIdeaService.passes_backtest_gate(
        {"profit_factor": 1.35, "max_drawdown_pct": 7.0}
    )
    assert not TradeIdeaService.passes_backtest_gate(
        {"profit_factor": 1.1, "max_drawdown_pct": 7.0}
    )
    assert not TradeIdeaService.passes_backtest_gate(
        {"profit_factor": 1.5, "max_drawdown_pct": 12.0}
    )


def test_profit_backtest_proxy(client):
    r = client.post(
        "/api/v1/backtest/run",
        json={"symbol": "PETR4", "strategy": "scalp_default", "period": "90d"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "profit_factor" in data
    assert "max_drawdown_pct" in data
    assert "job_id" in data


def test_pause_all_strategies(client):
    r = client.post("/api/v1/strategies/pause-all")
    assert r.status_code == 200
    assert "paused" in r.json()


def test_stock_options_chain(client):
    r = client.get("/api/v1/options/stock/PETR4")
    assert r.status_code == 200
    data = r.json()
    assert data.get("underlying") == "PETR4"


def test_board_review_partial(client):
    r = client.get("/board/partials/setup")
    assert r.status_code == 200
    assert "Setup" in r.text


def test_sector_strip_partial(client):
    r = client.get("/board/partials/sector-strip")
    assert r.status_code == 200
    assert "bb-sector-strip" in r.text
    assert "PETR4" in r.text or "Energia" in r.text


def test_confirm_step_partial_not_found(client):
    r = client.get("/board/partials/ideas/99999/confirm-step")
    assert r.status_code == 404
