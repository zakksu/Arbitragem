"""Tests for Trader Desk + motor journal (Phase A/B)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.main import create_app
from src.models import MotorJournal, get_session_factory, init_db
from src.services.motor_journal import append_journal, list_recent


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("BOARD_AUTH_ENABLED", "false")
    monkeypatch.setenv("BOARD_PASSWORD", "")
    init_db()
    return TestClient(create_app())


def test_motor_journal_append_and_list():
    init_db()
    session = get_session_factory()()
    try:
        session.query(MotorJournal).delete()
        session.commit()
        append_journal(session, "SCAN", "test scan", symbol="PETR4", level="info")
        append_journal(session, "FILL", "filled", symbol="PETR4", idea_id=1, level="fill")
        rows = list_recent(session, limit=10)
        assert len(rows) == 2
        assert rows[0]["phase"] == "SCAN"
        assert rows[1]["phase"] == "FILL"
    finally:
        session.close()


def test_trader_desk_partial(client):
    r = client.get("/board/partials/trader-desk")
    assert r.status_code == 200
    assert "bb-trader-desk" in r.text
    assert "Blotter" in r.text
    assert "Trader agent" in r.text
