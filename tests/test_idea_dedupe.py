"""Idea stack dedupe and kill-switch rationale guards."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import ScanResult, TradeIdea, get_session_factory, init_db
from src.services.trade_ideas import TradeIdeaService
from src.services.trade_product import build_trade_product, _clean_thesis


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'dedupe.db'}")
    get_settings.cache_clear()
    monkeypatch.setenv("SCANNER_OLLAMA_ON_SCAN", "false")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    init_db()
    return TestClient(create_app())


def test_clean_thesis_strips_kill_spam():
    t = _clean_thesis(
        "[Kill switch] Idea cancelled.\n" * 20,
        "PETR4 scalp long",
    )
    assert t == "PETR4 scalp long"
    assert "Kill switch" not in t


def test_list_ideas_for_stack_dedupes_symbol(client):
    session = get_session_factory()()
    session.add(
        TradeIdea(
            symbol="PETR4",
            structure_type="scalp_long",
            side="long",
            status="backtested",
            reliability=90,
            created_at=datetime.utcnow(),
        )
    )
    session.add(
        TradeIdea(
            symbol="PETR4",
            structure_type="scalp_long",
            side="long",
            status="backtested",
            reliability=70,
            created_at=datetime.utcnow(),
        )
    )
    session.commit()
    rows = TradeIdeaService(session).list_ideas_for_stack(limit=10)
    session.close()
    petr = [r for r in rows if r.symbol == "PETR4"]
    assert len(petr) == 1
    assert petr[0].reliability == 90


def test_kill_switch_does_not_duplicate_rationale(client):
    session = get_session_factory()()
    idea = TradeIdea(
        symbol="VALE3",
        structure_type="scalp_long",
        side="long",
        status="backtested",
        rationale="Original thesis",
    )
    session.add(idea)
    session.commit()
    iid = idea.id
    session.close()

    client.post("/api/v1/risk/kill-switch", json={"active": True, "reason": "test"})
    client.post("/api/v1/risk/kill-switch", json={"active": True, "reason": "test2"})
    client.post("/api/v1/risk/kill-switch", json={"active": False})

    session = get_session_factory()()
    updated = session.get(TradeIdea, iid)
    session.close()
    assert updated.status == "rejected"
    assert updated.rationale.count("[Kill switch]") == 1
