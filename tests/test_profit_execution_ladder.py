"""Profit execution ladder — mode resolution and assist."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import init_db


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ladder.db'}")
    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    init_db()
    return TestClient(create_app())


def test_resolve_paper_stub_when_paper_mode(monkeypatch):
    monkeypatch.setenv("PAPER_TRADING_MODE", "true")
    monkeypatch.setenv("PROFIT_EXEC_LADDER", "auto")
    get_settings.cache_clear()
    from src.services.profit_execution_ladder import resolve_active_mode

    assert resolve_active_mode() == "paper_stub"


def test_ladder_status_has_rungs(monkeypatch):
    monkeypatch.setenv("PAPER_TRADING_MODE", "true")
    get_settings.cache_clear()
    from src.services.profit_execution_ladder import build_ladder_status

    status = build_ladder_status()
    assert status["active_mode"] == "paper_stub"
    assert len(status["rungs"]) == 4
    ids = {r["id"] for r in status["rungs"]}
    assert ids == {"paper_stub", "manual_outbox", "ntsl_export", "dll_auto"}


def test_execution_ladder_api(client, monkeypatch):
    monkeypatch.setenv("PAPER_TRADING_MODE", "true")
    get_settings.cache_clear()
    r = client.get("/api/v1/integrations/profit/execution-ladder")
    assert r.status_code == 200
    assert r.json()["active_mode"] == "paper_stub"
