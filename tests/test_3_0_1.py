"""3.0.1 polish — DD display, header dedupe, HelpTip skeleton."""

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


def test_status_bar_no_duplicate_day_pnl(client):
    r = client.get("/board/partials/status")
    assert r.status_code == 200
    text = r.text
    assert "Balance" not in text
    assert "P&amp;L" not in text
    assert "Profit" in text
    assert "Clear" not in text


def test_status_bar_has_help_tip(client):
    r = client.get("/board/partials/status")
    assert "bb-help-tip" in r.text


def test_risk_cockpit_has_help_tip(client):
    r = client.get("/board/partials/risk-cockpit")
    assert r.status_code == 200
    assert "bb-help-tip" in r.text


def test_idea_stack_dd_missing_not_100(client, monkeypatch):
    monkeypatch.setattr(
        "src.web.router._list_ideas_sync",
        lambda limit=20: [
            {
                "id": 1,
                "symbol": "PETR4",
                "side": "long",
                "status": "backtested",
                "backtest_proof": {"profit_factor": 1.5},
                "reliability": 80,
            }
        ],
    )
    r = client.get("/board/partials/ideas")
    assert r.status_code == 200
    assert "100.0%" not in r.text
    assert "DD <strong>—</strong>" in r.text


def test_backtest_gate_without_drawdown_pct():
    assert TradeIdeaService.passes_backtest_gate({"profit_factor": 1.5})


def test_bootstrap_includes_profit_bridge_flag(client):
    r = client.get("/api/v1/bootstrap")
    assert r.status_code == 200
    data = r.json()
    assert "profit_bridge" in data
