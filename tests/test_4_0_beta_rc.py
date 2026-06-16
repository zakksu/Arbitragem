"""4.0-beta/rc API smoke tests."""

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import init_db


@pytest.fixture
def client(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    init_db()
    return TestClient(create_app())


def test_pulse_rail_api(client):
    r = client.get("/api/v1/pulse")
    assert r.status_code == 200
    data = r.json()
    assert "news" in data and "calendar" in data and "lesson" in data


def test_pulse_rail_partial(client):
    r = client.get("/board/partials/pulse-rail")
    assert r.status_code == 200
    assert "bb-pulse-rail" in r.text


def test_replay_run_sandbox(client):
    r = client.post(
        "/api/v1/replay/run",
        json={"strategy": "scalp_default", "symbol": "PETR4", "speed": 10, "mode": "sandbox"},
    )
    assert r.status_code == 200
    assert r.json()["mode"] == "sandbox"


def test_ntsl_arm(client, tmp_path, monkeypatch):
    monkeypatch.setattr("src.services.ntsl_arm.NTSL_DIR", tmp_path / "ntsl")
    r = client.post(
        "/api/v1/ntsl/arm",
        json={"symbol": "PETR4", "structure_type": "scalp", "side": "long"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "armed"


def test_kpi_history(client):
    for rng in ("today", "5d", "20d", "3mo"):
        r = client.get("/api/v1/kpi/history", params={"range": rng})
        assert r.status_code == 200
        assert r.json()["range"] == rng


def test_symbol_odds_endpoint(client):
    r = client.get("/api/v1/symbols/PETR4/odds", params={"structure_type": "scalp"})
    assert r.status_code == 200
    data = r.json()
    assert data["symbol"] == "PETR4"
    assert "win_rate_pct" in data
    assert data["source"] in ("journal", "backtest", "stub")


def test_replay_lab_partial(client):
    r = client.get("/board/partials/replay-lab", params={"symbol": "PETR4"})
    assert r.status_code == 200
    assert "bb-replay-lab" in r.text


def test_ntsl_arm_confirm_partial(client):
    r = client.get(
        "/board/partials/ntsl-arm-confirm",
        params={"symbol": "PETR4", "structure_type": "scalp", "side": "long"},
    )
    assert r.status_code == 200
    assert "ntsl-arm-modal" in r.text
    assert "Confirm arm" in r.text


def test_replay_lab_run_partial(client):
    r = client.post(
        "/board/partials/replay-lab/run",
        data={"symbol": "PETR4", "speed": "5"},
    )
    assert r.status_code == 200
    assert "job" in r.text.lower()


def test_trade_product_odds_source(client, monkeypatch):
    async def _fake_fetch(req, path):
        return {
            "symbol": "PETR4",
            "structure_type": "scalp",
            "side": "long",
            "score": 72,
            "thesis": "Test",
            "why_not_alternatives": [],
            "odds": {"profit_factor": 1.4, "source": "journal"},
            "chart_levels": {"entry": 38.0, "stop": 37.5, "target": 39.0},
            "legs": [],
        }

    monkeypatch.setattr("src.web.router._fetch_json", _fake_fetch)
    r = client.get("/board/partials/symbol/PETR4/trade-product")
    assert r.status_code == 200
    assert "bb-odds-source" in r.text
    assert "journal" in r.text


def test_watchlist_atr_cache(monkeypatch):
    from src.services.watchlist_enrich import _ATR_CACHE, _atr_pct_stub

    _ATR_CACHE.clear()
    calls = {"n": 0}
    orig = __import__("src.integrations.profit_bridge", fromlist=["get_profit_client"]).get_profit_client

    class FakeClient:
        def is_available(self):
            return True

        def get_session_candles(self, symbol):
            calls["n"] += 1
            return [{"high": 10.0, "low": 9.5}] * 5

    monkeypatch.setattr(
        "src.services.watchlist_enrich.get_profit_client",
        lambda: FakeClient(),
    )
    v1 = _atr_pct_stub("PETR4", 38.0, bridge_available=True)
    v2 = _atr_pct_stub("PETR4", 38.0, bridge_available=True)
    assert v1 == v2
    assert calls["n"] == 1
