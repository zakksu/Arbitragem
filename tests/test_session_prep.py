"""Session prep API and checklist."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import init_db


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'prep.db'}")
    get_settings.cache_clear()
    init_db()
    return TestClient(create_app())


def test_session_prep_api(client, monkeypatch):
    monkeypatch.setenv("PAPER_TRADING_MODE", "true")
    get_settings.cache_clear()
    r = client.get("/api/v1/session/prep")
    assert r.status_code == 200
    body = r.json()
    assert "steps_pre" in body
    assert "steps_during_paper" in body
    assert body["active_execution_mode"] == "paper_stub"


def test_session_prep_partial(client, monkeypatch):
    monkeypatch.setenv("PAPER_TRADING_MODE", "true")
    get_settings.cache_clear()
    r = client.get("/board/partials/session-prep")
    assert r.status_code == 200
    assert "session-prep-strip" in r.text
