"""3.0.1 polish — DD display, HelpTips, chart candles, header dedupe."""

import pytest
from fastapi.testclient import TestClient

from src import __version__
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


def test_version_is_4_0_beta():
    assert __version__ == "12.0.0"


def test_normalize_drawdown_pct_missing():
    assert TradeIdeaService.normalize_drawdown_pct({"profit_factor": 1.5}) is None
    assert TradeIdeaService.normalize_drawdown_pct({"max_drawdown": 1.0}) is None


def test_normalize_drawdown_pct_explicit():
    assert TradeIdeaService.normalize_drawdown_pct({"max_drawdown_pct": 5.8}) == 5.8


def test_backtest_gate_without_drawdown_pct():
    assert TradeIdeaService.passes_backtest_gate({"profit_factor": 1.5})


def test_backtest_gate_uses_pct_without_double_multiply():
    assert TradeIdeaService.passes_backtest_gate(
        {"profit_factor": 1.5, "max_drawdown_pct": 5.0}
    )
    assert not TradeIdeaService.passes_backtest_gate(
        {"profit_factor": 1.5, "max_drawdown_pct": 12.0}
    )


def test_status_bar_single_day_pnl(client):
    r = client.get("/board/partials/status")
    assert r.status_code == 200
    assert r.text.count("Day P&amp;L") == 1
    assert "Arbitragem Scalper" in r.text
    assert 'class="bb-pnl-source"' in r.text


def test_status_bar_help_tips(client):
    r = client.get("/board/partials/status")
    assert r.text.count("bb-help-tip") >= 5


def test_watchlist_help_tips(client):
    r = client.get("/board/partials/watchlist")
    assert r.status_code == 200
    assert r.text.count("bb-help-tip") >= 4


def test_idea_stack_dd_missing_not_100(client, monkeypatch):
    monkeypatch.setattr(
        "src.web.router._list_ideas_sync",
        lambda limit=20, symbol=None: [
            {
                "id": 1,
                "symbol": "PETR4",
                "side": "long",
                "status": "backtested",
                "backtest_proof": {"profit_factor": 1.5, "max_drawdown": 1.0},
                "dd_pct": None,
                "reliability": 80,
            }
        ],
    )
    r = client.get("/board/partials/ideas")
    assert r.status_code == 200
    assert "100.0%" not in r.text
    assert "DD <strong>—</strong>" in r.text


def test_idea_stack_help_tips(client, monkeypatch):
    monkeypatch.setattr(
        "src.web.router._list_ideas_sync",
        lambda limit=20, symbol=None: [
            {
                "id": 1,
                "symbol": "PETR4",
                "side": "long",
                "status": "backtested",
                "backtest_proof": {"profit_factor": 1.5, "max_drawdown_pct": 5.0},
                "dd_pct": 5.0,
                "reliability": 80,
            }
        ],
    )
    r = client.get("/board/partials/ideas")
    assert r.text.count("bb-help-tip") >= 2


def test_symbol_partial_chart_markup(client):
    r = client.get("/board/partials/symbol/PETR4")
    assert r.status_code == 200
    assert "lw-chart-PETR4" in r.text
    assert "data-candles" in r.text
    assert "bb-chart-canvas" in r.text


def test_profit_bridge_session_candles():
    from src.integrations.profit_bridge import ProfitBridgeClient

    rows = ProfitBridgeClient().get_session_candles("PETR4", bars=5)
    assert len(rows) == 5
    assert all("open" in c and "close" in c and "time" in c for c in rows)


def test_board_page_no_separate_risk_wrap(client):
    r = client.get("/board")
    assert r.status_code == 200
    assert "risk-cockpit-wrap" not in r.text


def test_structure_builder_create_idea_label(client):
    r = client.get("/board/partials/symbol/PETR4")
    assert "Create Idea" in r.text
    assert "Create loss" not in r.text
