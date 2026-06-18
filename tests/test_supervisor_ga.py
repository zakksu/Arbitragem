"""Supervisor GA backlog — VWAP, gates, archaeology insights, CEI, clear status."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import Trade, TradeIdea, init_db
from src.services.vwap import session_vwap, vwap_context


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ga.db'}")
    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("PAPER_TRADING_MODE", "true")
    init_db()
    return TestClient(create_app())


def test_session_vwap_from_candles():
    candles = [
        {"high": 10, "low": 9, "close": 9.5, "volume": 100},
        {"high": 11, "low": 10, "close": 10.5, "volume": 200},
    ]
    vwap = session_vwap(candles)
    assert vwap is not None
    assert 9.5 < vwap < 11.0


def test_vwap_reclaim_long():
    ctx = vwap_context(last=10.2, prev_last=9.8, vwap=10.0)
    assert ctx["vwap_reclaim_long"] is True


def test_idea_gates_endpoint(client):
    from src.models import get_session_factory

    session = get_session_factory()()
    idea = TradeIdea(symbol="PETR4", structure_type="scalp_long", side="long", status="detected")
    session.add(idea)
    session.commit()
    iid = idea.id
    session.close()

    r = client.get(f"/api/v1/ideas/{iid}/gates")
    assert r.status_code == 200
    body = r.json()
    assert body["idea_id"] == iid
    assert "can_confirm" in body
    assert "blockers" in body


def test_clear_router_status(client):
    r = client.get("/api/v1/execution/clear/status")
    assert r.status_code == 200
    body = r.json()
    assert body["paper_trading_mode"] is True
    assert body["live_enabled"] is False


def test_archaeology_insights(client):
    from src.models import get_session_factory

    session = get_session_factory()()
    session.add(
        Trade(
            external_id="arch-test-1",
            source="archaeology",
            symbol="PETR4",
            side="buy",
            quantity=100,
            price=38.0,
            pnl=50.0,
            executed_at=__import__("datetime").datetime.utcnow(),
        )
    )
    session.commit()
    session.close()

    r = client.get("/api/v1/archaeology/symbol/PETR4/insights")
    assert r.status_code == 200
    body = r.json()
    assert body["archaeology"]["trade_count"] >= 1


def test_archaeology_summary_api(client):
    from src.models import get_session_factory

    session = get_session_factory()()
    session.add(
        Trade(
            external_id="arch-sum-1",
            source="archaeology",
            symbol="VALE3",
            side="buy",
            quantity=100,
            price=62.0,
            pnl=20.0,
            executed_at=__import__("datetime").datetime.utcnow(),
        )
    )
    session.commit()
    session.close()

    r = client.get("/api/v1/archaeology/summary?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["total_trades"] >= 1
    assert body["source"] == "db"
    assert "top_symbols" in body
    assert "lanes" in body
    assert any(s["symbol"] == "VALE3" for s in body["top_symbols"])


def test_cei_parse_upload(client):
    csv_text = "Data;Ativo;Tipo;Quantidade;Preco;Resultado\n01/06/2025;VALE3;C;10;62,00;20,00\n"
    files = {"file": ("cei.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")}
    r = client.post("/api/v1/cei/parse", files=files)
    assert r.status_code == 200
    assert r.json()["row_count"] == 1


def test_cei_import_upload(client):
    csv_text = "Data;Ativo;Tipo;Quantidade;Preco;Resultado\n01/06/2025;VALE3;C;10;62,00;20,00\n"
    files = {"file": ("cei.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")}
    r = client.post("/api/v1/cei/import", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body.get("source_format") == "cei"
    assert body.get("imported", 0) >= 1


def test_session_vwap_endpoint(client, monkeypatch):
    class _Quote:
        last = 10.5
        bid = 10.4
        ask = 10.6

    class _Client:
        def get_quote(self, _sym):
            return _Quote()

        def get_session_candles(self, _sym):
            return [{"high": 10, "low": 9, "close": 9.5, "volume": 100}]

    monkeypatch.setattr(
        "src.integrations.profit_bridge.get_profit_client",
        lambda: _Client(),
    )
    r = client.get("/api/v1/symbols/PETR4/session-vwap")
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "PETR4"
    assert body["session_vwap"] is not None


def test_confirm_response_includes_gates(client):
    from src.models import get_session_factory

    session = get_session_factory()()
    idea = TradeIdea(symbol="PETR4", structure_type="scalp_long", side="long", status="detected")
    session.add(idea)
    session.commit()
    iid = idea.id
    session.close()

    r = client.post(f"/api/v1/ideas/{iid}/confirm", params={"paper_override": True})
    assert r.status_code == 200
    body = r.json()
    assert "gates" in body
    assert "can_confirm" in body["gates"]
