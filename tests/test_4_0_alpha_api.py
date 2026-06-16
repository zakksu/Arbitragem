"""4.0-alpha API — clocks, watchlist enrich, ideas filter, idea score."""

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import init_db
from src.services.idea_score import score_idea


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'api.db'}")
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("PROFIT_BRIDGE_AUTO_DETECT", "false")
    monkeypatch.setenv("SCANNER_OLLAMA_ON_SCAN", "false")
    init_db()
    return TestClient(create_app())


def test_market_clocks(client):
    r = client.get("/api/v1/market/clocks")
    assert r.status_code == 200
    data = r.json()
    assert "markets" in data
    ids = {m["id"] for m in data["markets"]}
    assert {"b3", "ny", "lon", "tyo", "sha"} <= ids
    for m in data["markets"]:
        assert m["status"] in ("open", "closed", "pre")
        assert "local_time" in m


def test_watchlist_enriched(client):
    r = client.get("/api/v1/watchlist/enriched")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    row = data["symbols"][0]
    assert "symbol" in row
    assert "idea_score" in row
    assert "atr_pct" in row
    assert "est_cost_brl" in row
    assert "bias" in row


def test_ideas_filter_by_symbol(client):
    r = client.get("/api/v1/ideas", params={"symbol": "PETR4", "limit": 5})
    assert r.status_code == 200
    data = r.json()
    assert data["symbol"] == "PETR4"
    for idea in data["ideas"]:
        assert idea["symbol"] == "PETR4"


def test_idea_score_range():
    high = score_idea(
        {
            "reliability": 85,
            "backtest_proof": {"profit_factor": 1.6},
            "walk_forward_pass": True,
            "status": "backtested",
            "rationale_tags": ["vwap_reclaim"],
        }
    )
    low = score_idea({"reliability": 20, "backtest_proof": {"profit_factor": 0.9}})
    assert 0 <= low <= 100
    assert 0 <= high <= 100
    assert high > low


def test_profit_pnl_sync_module():
    from src.models import get_session_factory
    from src.services.profit_pnl_sync import last_pnl_snapshot, sync_profit_pnl

    init_db()
    session = get_session_factory()()
    try:
        snap = sync_profit_pnl(session)
        assert "day_pnl" in snap
        assert last_pnl_snapshot() == snap
    finally:
        session.close()
