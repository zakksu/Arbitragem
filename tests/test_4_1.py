"""4.1 — WIN/WDO futures watchlist + read-only social signals."""

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import init_db
from src.services.futures_quotes import futures_session_status, get_futures_quotes
from src.services.futures_universe import load_futures_universe, symbol_list
from src.services.social_signals import get_social_signals


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / '41.db'}")
    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("FUTURES_WATCHLIST_ENABLED", "true")
    monkeypatch.setenv("SOCIAL_SIGNALS_ENABLED", "true")
    init_db()
    return TestClient(create_app())


def test_futures_universe():
    syms = symbol_list()
    assert "WINFUT" in syms
    assert "WDOFUT" in syms
    assert len(load_futures_universe()) == 2


def test_futures_stub_quotes():
    quotes = get_futures_quotes()
    assert quotes["WINFUT"].last > 100_000
    assert 4.0 < quotes["WDOFUT"].last < 7.0


def test_futures_session_badge():
    session = futures_session_status()
    assert session["session_status"] in ("open", "pre", "closed")
    assert session["market"] == "b3_futures"


def test_watchlist_includes_futures(client):
    r = client.get("/api/v1/watchlist/enriched")
    assert r.status_code == 200
    data = r.json()
    assert data["futures_count"] == 2
    symbols = {row["symbol"] for row in data["symbols"]}
    assert "WINFUT" in symbols
    assert "WDOFUT" in symbols
    win = next(x for x in data["futures"] if x["symbol"] == "WINFUT")
    assert win["asset_class"] == "future"
    assert win["session_status"] in ("open", "pre", "closed")
    assert win["session_label"]
    assert win["last"] > 100_000


def test_universe_futures_endpoint(client):
    r = client.get("/api/v1/universe/futures")
    assert r.status_code == 200
    body = r.json()
    assert len(body["symbols"]) == 2
    assert body["quotes"][0]["underlying"] in ("IBOV", "USD/BRL")


def test_social_signals_api(client):
    r = client.get("/api/v1/signals/social")
    assert r.status_code == 200
    data = r.json()
    assert data["read_only"] is True
    assert data["auto_trade"] is False
    assert data["count"] >= 3
    assert any(s["source"] == "twitter" for s in data["signals"])
    assert data["disclaimer"]
    assert "twitter" in data["sources_active"]
    assert data["fetched_at"]
    assert data["session"]["market"] == "b3_futures"
    assert data["freshness_minutes"] is not None


def test_social_signals_no_auto_trade():
    payload = get_social_signals(limit=5)
    for sig in payload["signals"]:
        assert sig["read_only"] is True
        assert sig["auto_trade"] is False


def test_social_signals_disabled(client, monkeypatch):
    monkeypatch.setenv("SOCIAL_SIGNALS_ENABLED", "false")
    get_settings.cache_clear()
    r = client.get("/api/v1/signals/social")
    assert r.json()["count"] == 0


def test_futures_watchlist_disabled(client, monkeypatch):
    monkeypatch.setenv("FUTURES_WATCHLIST_ENABLED", "false")
    get_settings.cache_clear()
    data = client.get("/api/v1/watchlist/enriched").json()
    assert data["futures_count"] == 0
    assert "WINFUT" not in {r["symbol"] for r in data["symbols"]}


def test_board_watchlist_futures_rows(client):
    r = client.get("/board/partials/watchlist")
    assert r.status_code == 200
    html = r.text
    assert "WINFUT" in html
    assert "WDOFUT" in html
    assert "bb-watch-row-futures" in html
    assert "bb-session-" in html


def test_board_pulse_social_chips(client):
    r = client.get("/board/partials/pulse-rail-legacy")
    assert r.status_code == 200
    html = r.text
    assert "bb-social-chips" in html
    assert "bb-social-disclaimer" in html
    assert "never auto-trade" in html.lower()
