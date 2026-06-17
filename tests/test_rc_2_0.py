"""2.0-rc Supervisor APIs — SSE, symbol report, lifecycle, execute, kill switch."""

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import Trade, TradeIdea, get_session_factory, init_db
from src.services.kill_switch import set_active
from src.services.paper_execution import paper_fill_price
from src.services.trade_ideas import TradeIdeaService


@pytest.fixture
def client(monkeypatch):
    get_settings.cache_clear()
    set_active(False)
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("SCANNER_OLLAMA_ON_SCAN", "false")
    monkeypatch.setenv("OLLAMA_ENABLED", "false")
    init_db()
    return TestClient(create_app())


def _idea_with_proof(session, **kwargs) -> TradeIdea:
    backtest_proof = kwargs.pop("backtest_proof", {"profit_factor": 1.5, "max_drawdown_pct": 5.0})
    idea = TradeIdea(
        symbol=kwargs.pop("symbol", "PETR4"),
        title=kwargs.pop("title", "test idea"),
        side=kwargs.pop("side", "long"),
        structure_type=kwargs.pop("structure_type", "scalp"),
        legs=kwargs.pop(
            "legs",
            [{"symbol": "PETR4", "side": "buy", "quantity": 100, "leg_type": "cash"}],
        ),
        status=kwargs.pop("status", "backtested"),
        backtest_proof=backtest_proof,
        **kwargs,
    )
    session.add(idea)
    session.commit()
    session.refresh(idea)
    return idea


def test_symbol_report_endpoint(client):
    r = client.get("/api/v1/symbols/PETR4/report")
    assert r.status_code == 200
    data = r.json()
    assert data["symbol"] == "PETR4"
    assert "narrative" in data
    assert "sector" in data
    assert data["cached"] is False
    r2 = client.get("/api/v1/symbols/PETR4/report")
    assert r2.json()["cached"] is True


def test_lifecycle_confirm_requires_backtest_gate(client):
    session = get_session_factory()()
    idea = _idea_with_proof(session, status="detected", backtest_proof=None)
    idea_id = idea.id
    session.close()

    r = client.post(f"/api/v1/ideas/{idea_id}/confirm")
    assert r.status_code == 400
    assert "Backtest gate" in r.json()["detail"]


def test_lifecycle_confirm_then_execute(client):
    session = get_session_factory()()
    idea = _idea_with_proof(session)
    idea_id = idea.id
    session.close()

    r = client.post(f"/api/v1/ideas/{idea_id}/confirm")
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

    r2 = client.post(f"/api/v1/ideas/{idea_id}/execute")
    assert r2.status_code == 200
    assert r2.json()["status"] == "executed"


def test_paper_override_skips_backtest_gate(client):
    session = get_session_factory()()
    idea = TradeIdea(
        symbol="VALE3",
        title="override",
        side="long",
        structure_type="scalp",
        legs=[{"symbol": "VALE3", "side": "buy", "quantity": 100, "leg_type": "cash"}],
        status="detected",
    )
    session.add(idea)
    session.commit()
    idea_id = idea.id
    session.close()

    r = client.post(f"/api/v1/ideas/{idea_id}/confirm?paper_override=true")
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"


def test_execute_applies_slippage(client):
    from datetime import datetime

    from src.integrations.profit_bridge import ProfitQuote

    q = ProfitQuote("PETR4", 38.00, 38.02, 38.01, 1000, datetime.utcnow())
    assert paper_fill_price(q, "buy") == 38.03
    assert paper_fill_price(q, "sell") == 37.99

    session = get_session_factory()()
    idea = _idea_with_proof(session, status="confirmed")
    idea_id = idea.id
    session.close()

    r = client.post(f"/api/v1/ideas/{idea_id}/execute")
    assert r.status_code == 200

    session = get_session_factory()()
    trade = session.query(Trade).order_by(Trade.id.desc()).first()
    assert trade is not None
    assert trade.raw_payload.get("slippage_model") == "spread_plus_1_tick"
    session.close()


def test_kill_switch_blocks_confirm_and_execute(client):
    session = get_session_factory()()
    idea = _idea_with_proof(session)
    idea_id = idea.id
    session.close()

    r = client.post("/api/v1/risk/kill-switch", json={"active": True, "reason": "test"})
    assert r.status_code == 200
    assert r.json()["active"] is True

    summary = client.get("/api/v1/risk/summary").json()
    assert summary["kill_switch_active"] is True
    assert summary["can_confirm_ideas"] is False
    assert summary["can_execute_ideas"] is False

    r2 = client.post(f"/api/v1/ideas/{idea_id}/confirm")
    assert r2.status_code == 400
    assert "sleeve" in r2.json()["detail"].lower() or "paused" in r2.json()["detail"].lower()

    client.post("/api/v1/risk/kill-switch", json={"active": False})


def test_stream_quotes_openapi(client):
    spec = client.get("/openapi.json").json()
    assert "/api/v1/stream/quotes" in spec["paths"]
    params = spec["paths"]["/api/v1/stream/quotes"]["get"]["parameters"]
    assert any(p.get("name") == "symbols" for p in params)
