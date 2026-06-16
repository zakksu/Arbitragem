"""Day P&L alignment — journal > Profit > Clear."""

from datetime import datetime

import pytest

from src.config import get_settings
from src.models import Trade, get_session_factory, init_db
from src.services.pnl_truth import resolve_day_pnl
from src.services.risk_summary import build_risk_summary


@pytest.fixture
def db_session(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("PROFIT_BRIDGE_AUTO_DETECT", "false")
    init_db()
    session = get_session_factory()()
    from datetime import time

    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    session.query(Trade).filter(Trade.executed_at >= today_start).delete()
    session.commit()
    yield session
    session.close()


def test_pnl_defaults_to_clear_when_no_journal(db_session):
    pnl = resolve_day_pnl(db_session)
    assert pnl["pnl_source"] == "clear"
    assert pnl["day_pnl"] == pytest.approx(125.50)


def test_journal_overrides_clear(db_session):
    db_session.add(
        Trade(
            symbol="PETR4",
            side="buy",
            quantity=100,
            price=36.0,
            pnl=42.0,
            executed_at=datetime.utcnow(),
            external_id="T-TEST-1",
        )
    )
    db_session.commit()
    pnl = resolve_day_pnl(db_session)
    assert pnl["pnl_source"] == "journal"
    assert pnl["day_pnl"] == pytest.approx(42.0)


def test_risk_summary_includes_pnl_source(db_session):
    from src.services.kill_switch import set_active

    set_active(False)
    summary = build_risk_summary(db_session)
    assert summary["pnl_source"] in ("journal", "profit", "clear")
    assert "profit_day_pnl" in summary
