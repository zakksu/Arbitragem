"""Golden path mode — PETR4-only universe and checklist (Release 7.0)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import MotorJournal, TradeIdea, get_session_factory, init_db
from src.services.golden_path import evaluate_golden_path
from src.services.motor_journal import append_journal
from src.services.trade_ideas import TradeIdeaService


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("BOARD_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    init_db()
    return TestClient(create_app())


def test_golden_path_mode_config(monkeypatch):
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.golden_path_mode is True
    assert settings.scanner_symbol_list == ["PETR4"]


def test_golden_path_evaluate_structure():
    init_db()
    session = get_session_factory()()
    try:
        data = evaluate_golden_path(session)
        assert data["symbol"] == "PETR4"
        assert len(data["items"]) == 7
        assert "all_green" in data
        assert "sessions_green_count" in data
    finally:
        session.close()


def test_golden_path_all_green_when_checks_pass(monkeypatch):
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    get_settings.cache_clear()
    init_db()
    session = get_session_factory()()
    try:
        svc = TradeIdeaService(session)
        idea = svc.quick_seed_paper_idea("PETR4")
        idea.backtest_proof = {
            "profit_factor": 1.5,
            "max_drawdown_pct": 5.0,
            "trades": 20,
        }
        idea.status = "backtested"
        session.commit()

        append_journal(session, "FILL", "test fill", symbol="PETR4", level="fill")
        for _ in range(5):
            append_journal(session, "JOURNAL", "Cycle done — 0 actions, 0 errors", level="info")

        data = evaluate_golden_path(session)
        assert data["items"][0]["ok"] is True
        assert data["items"][1]["ok"] is True
        assert data["items"][2]["ok"] is True
    finally:
        session.close()


def test_golden_path_partial_200(client):
    r = client.get("/board/partials/golden-path")
    assert r.status_code == 200
    assert "bb-golden-path" in r.text
    assert "PETR4" in r.text


def test_ops_panel_partial_200(client):
    r = client.get("/board/partials/ops-panel")
    assert r.status_code == 200
    assert "bb-ops-strip" in r.text
    assert "Tests" in r.text


def test_board_shows_golden_path_slot(client):
    r = client.get("/board")
    assert r.status_code == 200
    assert "bb-golden-path-slot" in r.text
    assert "ops-panel-strip" in r.text


def test_golden_path_api(client):
    r = client.get("/api/v1/golden-path")
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "PETR4"
    assert len(body["items"]) == 7


def test_ops_memory_api(client):
    r = client.get("/api/v1/ops/memory")
    assert r.status_code == 200
    body = r.json()
    assert "motor_cycle_ms" in body
    assert "ram_budget_mb" in body
