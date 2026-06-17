"""Profit execution + orchestrator autonomy via Profit bridge."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.config import get_settings
from src.models import TradeIdea, get_session_factory, init_db
from src.services.capital_manager import apply_sizing_to_legs, size_quantity_for_idea
from src.services.profit_execution import pending_tickets, submit_order
from src.services.trade_ideas import TradeIdeaService
from src.services.trading_orchestrator import run_orchestrator_cycle
from src.services.trading_sleeves import set_all


@pytest.fixture
def db_session(monkeypatch):
    get_settings.cache_clear()
    init_db()
    session = get_session_factory()()
    yield session
    session.close()


def test_size_quantity_from_stop(monkeypatch):
    monkeypatch.setenv("PAPER_CAPITAL_BRL", "10000")
    get_settings.cache_clear()
    idea = {
        "symbol": "PETR4",
        "side": "long",
        "entry_price": 40.0,
        "stop_price": 39.0,
        "legs": [{"symbol": "PETR4", "side": "buy", "quantity": 100}],
    }
    qty = size_quantity_for_idea(idea)
    assert qty >= 100
    assert qty % 100 == 0
    sized = apply_sizing_to_legs(idea)
    assert sized[0]["quantity"] == qty


def test_submit_order_offline_stub(monkeypatch):
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    get_settings.cache_clear()
    result = submit_order(symbol="PETR4", side="buy", quantity=100, idea_id=1)
    assert result["status"] == "filled"
    assert result["symbol"] == "PETR4"
    assert result.get("ticket_id")


def test_pending_tickets_empty_when_bridge_off(monkeypatch):
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    get_settings.cache_clear()
    assert pending_tickets() == []


def test_execute_idea_profit_backend(db_session, monkeypatch):
    monkeypatch.setenv("EXECUTION_BACKEND", "profit")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    get_settings.cache_clear()

    idea = TradeIdea(
        symbol="VALE3",
        structure_type="scalp",
        side="long",
        status="confirmed",
        reliability=80.0,
        entry_price=57.0,
        stop_price=56.5,
        target_price=58.0,
        legs=[{"symbol": "VALE3", "side": "buy", "quantity": 100, "leg_type": "cash"}],
        confirmed_at=datetime.utcnow(),
    )
    db_session.add(idea)
    db_session.commit()

    svc = TradeIdeaService(db_session)
    executed = svc.execute_idea(idea.id)
    assert executed.status == "executed"
    from src.models import Trade

    trade = db_session.query(Trade).first()
    assert trade is not None
    assert trade.source == "profit"


def test_orchestrator_autonomy_profit_path(monkeypatch):
    monkeypatch.setenv("AUTONOMY_ENABLED", "true")
    monkeypatch.setenv("EXECUTION_BACKEND", "profit")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("PAPER_TRADING_MODE", "true")
    monkeypatch.setenv("AUTO_TRADING_ON_SLEEVES", "true")
    get_settings.cache_clear()
    set_all(True)
    init_db()

    session = get_session_factory()()
    idea = TradeIdea(
        symbol="PETR4",
        title="orchestrator test",
        side="long",
        structure_type="scalp",
        legs=[{"symbol": "PETR4", "side": "buy", "quantity": 100, "leg_type": "cash"}],
        status="backtested",
        reliability=85,
        backtest_proof={"profit_factor": 1.6, "max_drawdown_pct": 4.0},
    )
    session.add(idea)
    session.commit()

    mock_scanner = MagicMock()
    mock_scanner.run_daily_scan.return_value = None
    monkeypatch.setattr("src.services.trading_orchestrator.PatternScanner", lambda s: mock_scanner)
    monkeypatch.setattr(
        "src.services.trading_orchestrator._scan_is_stale",
        lambda s, max_age_minutes=20: False,
    )
    monkeypatch.setattr("src.services.trading_orchestrator.b3_session_open", lambda: True)

    out = run_orchestrator_cycle(session)
    assert out.get("active") is True
    autonomy = out.get("autonomy") or {}
    assert autonomy.get("actions") or autonomy.get("skipped") in (
        None,
        "daily_trade_cap",
        "risk_gate_blocked",
    )
    session.close()
