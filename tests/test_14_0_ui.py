"""Release 14.0 — Hybrid Cockpit tab shell + journal off desk."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import init_db
from src.services.board_layout import BOARD_TABS, board_tab_metadata


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 't14.db'}")
    monkeypatch.setenv("BOARD_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    init_db()
    return TestClient(create_app())


def test_board_tab_metadata():
    meta = board_tab_metadata()
    assert meta["default_tab"] == "desk"
    assert len(meta["tabs"]) == 3
    ids = {t["id"] for t in BOARD_TABS}
    assert ids == {"desk", "journal", "pnl"}


def test_board_has_tab_bar_not_journal_on_desk(client: TestClient):
    r = client.get("/board")
    assert r.status_code == 200
    assert "bb-tab-bar" in r.text
    assert "bb-tab-pill" in r.text
    assert "trade-journal-slot" not in r.text
    assert "bb-panel-desk" in r.text


def test_board_tab_journal_query(client: TestClient):
    r = client.get("/board?tab=journal")
    assert r.status_code == 200
    assert 'data-tab="journal"' in r.text


def test_journal_tab_partial(client: TestClient):
    r = client.get("/board/partials/journal-tab")
    assert r.status_code == 200
    assert "bb-journal-tab" in r.text
    assert "Export CSV" in r.text
    assert "bb-journal-filter" in r.text


def test_journal_tab_range_today(client: TestClient):
    r = client.get("/board/partials/journal-tab?range=today")
    assert r.status_code == 200
    assert "bb-journal-tab" in r.text


def test_pnl_tab_partial(client: TestClient):
    r = client.get("/board/partials/pnl-tab")
    assert r.status_code == 200
    assert "pnl-tab-root" in r.text
    assert "pnl-intraday-chart" in r.text


def test_board_tabs_api(client: TestClient):
    r = client.get("/api/v1/board/tabs")
    assert r.status_code == 200
    body = r.json()
    assert body["default_tab"] == "desk"


def test_pnl_intraday_api(client: TestClient):
    r = client.get("/api/v1/pnl/intraday")
    assert r.status_code == 200
    body = r.json()
    assert "day_pnl_brl" in body
    assert "points" in body or "buckets" in body


def test_blackboard_14_css_linked(client: TestClient):
    r = client.get("/board")
    assert "blackboard_14_0.css" in r.text


def test_pnl_tab_range_5d(client: TestClient):
    r = client.get("/board/partials/pnl-tab?range=5d")
    assert r.status_code == 200
    assert "pnl-tab-root" in r.text


def test_journal_note_patch_api(client: TestClient):
    from datetime import datetime

    from src.models import Trade, get_session_factory

    session = get_session_factory()()
    t = Trade(
        external_id="j14",
        source="paper",
        symbol="PETR4",
        side="buy",
        quantity=100,
        price=38.0,
        executed_at=datetime.utcnow(),
    )
    session.add(t)
    session.commit()
    tid = t.id
    session.close()

    r = client.patch(f"/api/v1/trades/{tid}/note", json={"note": "scalp A"})
    assert r.status_code == 200
    assert r.json()["journal_note"] == "scalp A"
