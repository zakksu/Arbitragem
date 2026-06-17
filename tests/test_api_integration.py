"""API integration tests for Agent A/B contract."""

from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import init_db


def _client():
    get_settings.cache_clear()
    init_db()
    return TestClient(create_app())


def test_health_includes_alerts_fields():
    r = _client().get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert "alerts_enabled" in data
    assert "paper_trading_mode" in data
    assert "scanner_mode" in data
    assert data["scanner_symbol_count"] >= 1


def test_scanner_insights():
    r = _client().get("/api/v1/scanner/insights")
    assert r.status_code == 200
    assert "insights" in r.json()


def test_ibov_universe():
    r = _client().get("/api/v1/universe/ibov-top20")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 20


def test_filipe_core14_universe():
    r = _client().get("/api/v1/universe/filipe-core14")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 14
    assert "sector_baskets" in data


def test_ideas_endpoint():
    r = _client().get("/api/v1/ideas")
    assert r.status_code == 200
    assert "ideas" in r.json()


def test_setup_status():
    r = _client().get("/api/v1/setup/status")
    assert r.status_code == 200
    data = r.json()
    assert "steps" in data
    assert data.get("release", "").startswith("10.")


def test_board_page():
    r = _client().get("/board")
    assert r.status_code == 200
    assert "Blackboard" in r.text


def test_bova_option_chain():
    from src.integrations.profit_bridge import ProfitBridgeClient

    chain = ProfitBridgeClient().get_bova_option_chain()
    assert chain["underlying"] == "BOVA11"
    assert len(chain.get("calls", [])) >= 1


def test_profit_integration_test():
    r = _client().get("/api/v1/integrations/profit/test")
    assert r.status_code == 200
    assert "available" in r.json()


def test_system_events():
    r = _client().get("/api/v1/system/events")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_alerts_status():
    r = _client().get("/api/v1/alerts/status")
    assert r.status_code == 200
    assert "configured" in r.json()


def test_list_backtests_empty_ok():
    r = _client().get("/api/v1/backtests")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_optimizations_empty_ok():
    r = _client().get("/api/v1/optimizations")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_risk_summary_endpoint():
    r = _client().get("/api/v1/risk/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("ok", "warning", "blocked")
    assert "loss_limit_used_pct" in data
