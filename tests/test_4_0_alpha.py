"""4.0-alpha — risk profile, Profit P&L, clocks, idea score, watchlist enrich."""

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import init_db
from src.services.idea_score import score_idea
from src.services.market_clocks import get_market_clocks


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'alpha.db'}")
    get_settings.cache_clear()
    monkeypatch.setenv("SCANNER_OLLAMA_ON_SCAN", "false")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    init_db()
    return TestClient(create_app())


def test_risk_profile_defaults(client):
    r = client.get("/api/v1/risk/profile")
    assert r.status_code == 200
    data = r.json()
    assert data["max_daily_loss_brl"] == 500.0
    assert data["max_open_positions"] >= 1


def test_risk_profile_put(client):
    r = client.put("/api/v1/risk/profile", json={"max_daily_loss_brl": 600.0})
    assert r.status_code == 200
    assert r.json()["max_daily_loss_brl"] == 600.0


def test_profit_pnl_endpoint(client):
    r = client.get("/api/v1/profit/pnl")
    assert r.status_code == 200
    data = r.json()
    assert "day_pnl" in data
    assert data["pnl_source"] in ("journal", "profit", "clear")


def test_market_clocks(client):
    r = client.get("/api/v1/market/clocks")
    assert r.status_code == 200
    data = r.json()
    assert len(data["markets"]) == 5
    ids = {m["id"] for m in data["markets"]}
    assert "b3" in ids and "ny" in ids


def test_market_clocks_service():
    clocks = get_market_clocks()
    assert clocks["markets"][0]["local_time"]


def test_idea_score_range():
    s = score_idea({"reliability": 75, "status": "detected", "backtest_proof": {"profit_factor": 1.5}})
    assert 0 <= s <= 100


def test_watchlist_enriched(client):
    r = client.get("/api/v1/watchlist/enriched")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    row = data["symbols"][0]
    assert "idea_score" in row
    assert "atr_pct" in row


def test_ideas_symbol_filter(client):
    r = client.get("/api/v1/ideas", params={"symbol": "PETR4", "limit": 5})
    assert r.status_code == 200
    assert "symbol" in r.json()


def test_risk_profile_drawer(client):
    r = client.get("/board/partials/risk-profile")
    assert r.status_code == 200
    assert "Risk Profile" in r.text
    assert "max_daily_loss_brl" in r.text or "Max daily loss" in r.text


def test_world_clocks_partial(client):
    r = client.get("/board/partials/world-clocks")
    assert r.status_code == 200
    assert "bb-clock-chip" in r.text


def test_status_scalper_brand(client):
    r = client.get("/board/partials/status")
    assert "Arbitragem Scalper" in r.text
