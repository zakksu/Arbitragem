"""Release 14.0 — PnL intraday + projection backend tests."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src import __version__
from src.config import get_settings
from src.main import create_app
from src.models import Trade, init_db


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'pnl14.db'}")
    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    init_db()
    return TestClient(create_app())


def test_version_14_0_alpha():
    assert __version__ == "14.0.0-alpha"


def test_pnl_intraday_empty(client):
    r = client.get("/api/v1/pnl/intraday")
    assert r.status_code == 200
    body = r.json()
    assert "buckets" in body
    assert "lanes" in body
    assert body["lanes"]["cash"] == 0.0


def test_pnl_intraday_with_trades(client):
    from src.models import get_session_factory

    session = get_session_factory()()
    session.add(
        Trade(
            external_id="p1",
            source="paper",
            symbol="PETR4",
            side="buy",
            quantity=100,
            price=38.0,
            pnl=20.0,
            fees=0.5,
            executed_at=datetime.utcnow(),
        )
    )
    session.commit()
    session.close()

    r = client.get("/api/v1/pnl/intraday")
    body = r.json()
    assert body["trades_today"] >= 1
    assert body["lanes"]["cash"] != 0.0 or body["buckets"][-1]["cumulative_brl"] != 0


def test_pnl_projection_estimate(client):
    r = client.get("/api/v1/pnl/projection")
    assert r.status_code == 200
    body = r.json()
    assert body["model"] == "expectancy_estimate"
    assert "projected_eod_brl" in body
    assert "session_remaining_min" in body
    assert body.get("label")


def test_board_tabs_metadata(client):
    r = client.get("/api/v1/board/tabs")
    assert r.status_code == 200
    tabs = r.json()["tabs"]
    assert len(tabs) == 3
    assert {t["id"] for t in tabs} == {"desk", "journal", "pnl"}


def test_board_desk_no_inline_journal(client):
    r = client.get("/board")
    assert r.status_code == 200
    assert "trade-journal-slot" not in r.text
    assert "bb-tab-bar" in r.text
    assert "bb-panel-desk" in r.text


def test_journal_tab_partial(client):
    r = client.get("/board/partials/journal-tab?range=today")
    assert r.status_code == 200
    assert "bb-journal-tab" in r.text
    assert "Trade Journal" in r.text


def test_pnl_tab_partial(client):
    r = client.get("/board/partials/pnl-tab")
    assert r.status_code == 200
    assert "bb-pnl-tab" in r.text
    assert "Day P" in r.text or "day_pnl" in r.text.lower()


def test_patch_trade_note(client):
    from src.models import get_session_factory

    session = get_session_factory()()
    t = Trade(
        external_id="n1",
        source="paper",
        symbol="VALE3",
        side="sell",
        quantity=100,
        price=62.0,
        executed_at=datetime.utcnow(),
    )
    session.add(t)
    session.commit()
    tid = t.id
    session.close()

    r = client.patch(f"/api/v1/trades/{tid}/note", json={"note": "VWAP reclaim A+"})
    assert r.status_code == 200
    assert r.json()["journal_note"] == "VWAP reclaim A+"


def test_journal_desk_filters(client):
    r = client.get("/api/v1/journal/desk?range_key=today&symbol=PETR4")
    assert r.status_code == 200
    assert r.json()["filters"]["symbol"] == "PETR4"
