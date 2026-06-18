"""Autonomy autopilot + motor FILL journal tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.models import MotorJournal, init_db
from src.services.autonomy_fast_track import autonomy_gate_snapshot, spread_motor_journal_days
from src.services.motor_journal import append_journal
from src.services.structure_types import STRUCTURE_CATALOG
from src.services.trader_agent import run_trader_cycle


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'auto.db'}")
    monkeypatch.setenv("PAPER_TRADING_MODE", "true")
    monkeypatch.setenv("AUTO_TRADING_ON_SLEEVES", "true")
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    from src.config import get_settings

    get_settings.cache_clear()
    init_db()
    from src.models import get_session_factory

    session = get_session_factory()()
    yield session
    session.close()


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'apic.db'}")
    monkeypatch.setenv("BOARD_AUTH_ENABLED", "false")
    from src.main import create_app

    init_db()
    return TestClient(create_app())


def test_quick_seed_rotates_scalp_structures(db_session):
    from src.services.trade_ideas import TradeIdeaService

    svc = TradeIdeaService(db_session)
    structures = set()
    for sym in ("PETR4", "VALE3", "ITUB4", "BBDC4", "ABEV3"):
        idea = svc.quick_seed_paper_idea(sym)
        structures.add(idea.structure_type)
    assert "stock_scalp_vwap" in structures or "pulse_scalp" in structures


def test_replay_strategy_for_structure():
    from src.services.structure_types import replay_strategy_for_structure

    assert replay_strategy_for_structure("stock_scalp_vwap") == "s1_vwap_reclaim"
    assert replay_strategy_for_structure("pulse_scalp") == "s5_pulse"
    ids = {row["id"] for row in STRUCTURE_CATALOG}
    assert "stock_scalp_vwap" in ids
    assert "pulse_scalp" in ids


def test_trader_cycle_logs_fill_on_execute(db_session, monkeypatch):
    from src.config import get_settings
    from src.services.trade_ideas import TradeIdeaService
    from src.services.trading_sleeves import set_all

    get_settings.cache_clear()
    set_all(True)
    svc = TradeIdeaService(db_session)
    idea = svc.quick_seed_paper_idea("PETR4")
    idea.status = "confirmed"
    db_session.commit()

    monkeypatch.setattr(
        "src.services.trading_orchestrator.run_orchestrator_cycle",
        lambda s: {
            "autonomy": {
                "actions": [
                    {"action": "execute", "idea_id": idea.id, "symbol": "PETR4", "mode": "paper"}
                ],
                "errors": [],
            },
            "errors": [],
        },
    )
    run_trader_cycle(db_session)
    fills = db_session.query(MotorJournal).filter(MotorJournal.phase == "FILL").all()
    assert len(fills) >= 1


def test_fast_track_spread_days(db_session, monkeypatch):
    monkeypatch.setenv("AUTONOMY_FAST_TRACK", "true")
    from src.config import get_settings

    get_settings.cache_clear()
    for i in range(8):
        append_journal(db_session, "JOURNAL", f"row {i}", commit=False)
    db_session.commit()
    out = spread_motor_journal_days(db_session, days=5)
    assert out["ok"] is True
    assert out["distinct_days"] >= 2


def test_autonomy_gates_api(client: TestClient):
    r = client.get("/api/v1/autonomy/gates")
    assert r.status_code == 200
    body = r.json()
    assert "golden_path" in body
    assert "phase_c" in body


def test_autonomy_gate_snapshot_shape(db_session):
    snap = autonomy_gate_snapshot(db_session)
    assert "paper_validation" in snap
