"""Trade ideas API (2.0 Idea Stack)."""

import pytest

from src.config import get_settings
from src.models import ScanResult, get_session_factory, init_db
from src.services.scanner import PatternScanner
from src.services.trade_ideas import TradeIdeaService


@pytest.fixture
def db_session(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("SCANNER_MODE", "filipe_core14")
    monkeypatch.setenv("SCANNER_INCLUDE_BOVA_OPTIONS", "false")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("SCANNER_OLLAMA_ON_SCAN", "false")

    class FakeOllama:
        def is_available(self):
            return False

    monkeypatch.setattr("src.services.scanner.get_ollama_client", lambda: FakeOllama())

    init_db()
    session = get_session_factory()()
    yield session
    session.close()


def test_generate_and_list_ideas(db_session):
    PatternScanner(db_session).run_daily_scan()
    svc = TradeIdeaService(db_session)
    created = svc.generate_from_latest_scan(limit=5)
    assert len(created) >= 1
    listed = svc.list_ideas(limit=10)
    assert len(listed) >= 1
    assert listed[0].symbol
    assert listed[0].reliability >= 0


def test_confirm_idea_paper(db_session):
    PatternScanner(db_session).run_daily_scan()
    svc = TradeIdeaService(db_session)
    idea = svc.generate_from_latest_scan(limit=1)[0]
    idea.backtest_proof = {"profit_factor": 1.5, "max_drawdown_pct": 5.0}
    idea.status = "backtested"
    db_session.commit()
    confirmed = svc.confirm_idea(idea.id)
    assert confirmed.status == "confirmed"
    executed = svc.execute_idea(idea.id)
    assert executed.status == "executed"
