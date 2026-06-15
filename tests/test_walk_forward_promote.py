"""Walk-forward auto-promotion (3.0-beta)."""

import pytest

from src.config import get_settings
from src.models import TradeIdea, get_session_factory, init_db
from src.services.walk_forward_promotion import run_walk_forward_promotion


@pytest.fixture
def db_session(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("SCANNER_OLLAMA_ON_SCAN", "false")
    init_db()
    session = get_session_factory()()
    yield session
    session.close()


def test_walk_forward_promote_endpoint(client):
    r = client.post("/api/v1/walk-forward/promote")
    assert r.status_code == 200
    data = r.json()
    assert "promoted" in data
    assert "runs_completed" in data


def test_walk_forward_promotion_creates_tagged_idea(db_session):
    result = run_walk_forward_promotion(db_session, folds=3)
    assert result["runs_completed"] >= 1
    ideas = db_session.query(TradeIdea).all()
    wf_ideas = [
        i
        for i in ideas
        if "walk_forward_pass" in (i.rationale_tags or [])
        and (i.backtest_proof or {}).get("walk_forward_folds_passed") is not None
    ]
    if result["promoted"] > 0:
        assert len(wf_ideas) >= 1


@pytest.fixture
def client(monkeypatch):
    from fastapi.testclient import TestClient
    from src.main import create_app

    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("SCANNER_OLLAMA_ON_SCAN", "false")
    init_db()
    return TestClient(create_app())
