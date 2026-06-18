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


def test_status_bar_single_kpi_strip(client):
    r = client.get("/board/partials/status")
    assert r.status_code == 200
    text = r.text
    assert text.count("Day P&amp;L") == 1
    assert "Arbitragem Scalper" in text
    assert 'class="bb-pnl-source"' in text


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
        lambda limit=20, symbol=None: [
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


def test_normalize_drawdown_pct_missing():
    assert TradeIdeaService.normalize_drawdown_pct({"profit_factor": 1.5}) is None


def test_version_is_4_0_beta():
    from src import __version__

    assert __version__ == "14.0.0"


def test_bootstrap_includes_profit_bridge_flag(client):
    r = client.get("/api/v1/bootstrap")
    assert r.status_code == 200
    data = r.json()
    assert "profit_bridge" in data
