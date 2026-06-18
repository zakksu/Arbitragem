"""Filipe Core17 universe + scanner mode (11.0 A11.10)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import init_db
from src.services.filipe_universe import (
    CORE17_SECTOR_BASKETS,
    core17_symbol_list,
    load_filipe_core17,
)


def test_core17_count():
    symbols = load_filipe_core17()
    assert len(symbols) == 17
    syms = core17_symbol_list()
    assert "RADL3" in syms
    assert "MGLU3" in syms
    assert "BOVA11" in syms
    assert "PETR4" in syms


def test_core17_sector_baskets():
    assert "RADL3" in CORE17_SECTOR_BASKETS["varejo"]
    assert "BOVA11" in CORE17_SECTOR_BASKETS["index"]


def test_scanner_mode_core17(monkeypatch):
    monkeypatch.setenv("SCANNER_MODE", "filipe_core17")
    monkeypatch.setenv("GOLDEN_PATH_MODE", "false")
    get_settings.cache_clear()
    syms = get_settings().scanner_symbol_list
    assert "RADL3" in syms
    assert len(syms) >= 17


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'c17.db'}")
    get_settings.cache_clear()
    init_db()
    return TestClient(create_app())


def test_filipe_core17_universe_api(client: TestClient):
    r = client.get("/api/v1/universe/filipe-core17")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 17
    assert body["scanner_mode"] == "filipe_core17"
    assert "varejo" in body["sector_baskets"]
    assert "RADL3" in body["sectors"].get("varejo", [])


def test_knowledge_ingest_insights_api(client: TestClient, tmp_path, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_ENABLED", "true")
    get_settings.cache_clear()
    insights = tmp_path / "b3_history_insights.json"
    insights.write_text(
        '{"summary":{"archaeology_trade_count":10,"unique_symbols":3},'
        '"core17_insights":{"PETR4":{"archaeology":{"trade_count":5,"net_pnl":120,"win_rate":0.6}}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "src.services.knowledge.insights_ingest._INSIGHTS",
        insights,
    )
    r = client.post("/api/v1/knowledge/ingest/insights")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True or body.get("chunks", 0) > 0


def test_motor_universe_core17_queue(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'motor.db'}")
    monkeypatch.setenv("SCANNER_MODE", "filipe_core17")
    get_settings.cache_clear()
    init_db()
    from src.models import get_session_factory
    from src.services.motor_universe import motor_universe_policy

    session = get_session_factory()()
    body = motor_universe_policy(session)
    session.close()
    assert body["universe_mode"] == "filipe_core17"
    assert body["universe_count"] == 17
    assert len(body["queued"]) <= 12


def test_core17_options_refresh_api(client: TestClient):
    r = client.post("/api/v1/options/core17/refresh")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert body.get("rows", 0) >= 1
