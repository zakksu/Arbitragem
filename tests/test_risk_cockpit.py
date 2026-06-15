"""Risk cockpit API and portfolio gates (3.0-beta)."""

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.models import TradeIdea, get_session_factory, init_db
from src.services.risk_cockpit import build_risk_cockpit, confirm_blocked_by_portfolio
from src.services.trade_ideas import TradeIdeaService


@pytest.fixture
def client(monkeypatch):
    from src.main import create_app

    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("SCANNER_OLLAMA_ON_SCAN", "false")
    init_db()
    return TestClient(create_app())


def test_risk_cockpit_endpoint(client):
    r = client.get("/api/v1/risk/cockpit")
    assert r.status_code == 200
    data = r.json()
    assert "net_delta" in data
    assert "gate_status" in data
    assert "margin_estimate_brl" in data
    assert "max_net_delta" in data


def test_portfolio_delta_gate_blocks_confirm(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("MAX_PORTFOLIO_NET_DELTA", "0.01")
    init_db()
    session = get_session_factory()()
    try:
        idea = TradeIdea(
            symbol="PETR4",
            structure_type="scalp_long",
            side="long",
            status="backtested",
            backtest_proof={"profit_factor": 1.5, "max_drawdown_pct": 5.0},
            legs=[
                {"symbol": "PETR4", "side": "buy", "quantity": 10000, "leg_type": "cash"},
            ],
        )
        session.add(idea)
        session.commit()
        session.refresh(idea)
        msg = confirm_blocked_by_portfolio(session, idea.legs)
        assert msg is not None
        with pytest.raises(ValueError, match="net delta"):
            TradeIdeaService(session).confirm_idea(idea.id)
    finally:
        session.close()


def test_risk_cockpit_board_partial(client):
    r = client.get("/board/partials/risk-cockpit")
    assert r.status_code == 200
    assert "bb-risk-cockpit" in r.text
    assert "Net" in r.text
