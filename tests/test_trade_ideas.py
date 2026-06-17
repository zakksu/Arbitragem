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
    from datetime import datetime

    from src.models import TradeIdea

    db_session.query(TradeIdea).filter(TradeIdea.symbol == "WEGE3").delete()
    db_session.commit()

    PatternScanner(db_session).run_daily_scan()
    latest = (
        db_session.query(ScanResult.scan_date)
        .order_by(ScanResult.scan_date.desc())
        .first()
    )
    scan_date = latest[0] if latest else datetime.utcnow()
    db_session.add(
        ScanResult(
            symbol="WEGE3",
            scan_date=scan_date,
            spike_score=90.0,
            alert_level="info",
            pattern_tags=["volume_spike", "scalp_long"],
            raw_data={
                "reliability": 78.0,
                "side_bias": "long",
                "stop_ticks": 5,
                "target_ticks": 8,
                "last": 41.5,
            },
        )
    )
    db_session.commit()
    svc = TradeIdeaService(db_session)
    created = svc.generate_from_latest_scan(limit=5)
    assert len(created) >= 1
    listed = svc.list_ideas(limit=10)
    assert len(listed) >= 1
    assert listed[0].symbol
    assert listed[0].reliability >= 0


def test_confirm_idea_paper(db_session):
    from datetime import datetime

    from src.models import ScanResult, TradeIdea

    scan = ScanResult(
        symbol="PETR4",
        scan_date=datetime.utcnow(),
        spike_score=70.0,
        alert_level="info",
    )
    db_session.add(scan)
    db_session.flush()
    idea = TradeIdea(
        symbol="PETR4",
        structure_type="scalp",
        side="long",
        status="backtested",
        reliability=80.0,
        entry_price=38.0,
        backtest_proof={"profit_factor": 1.5, "max_drawdown_pct": 5.0},
        scan_result_id=scan.id,
    )
    db_session.add(idea)
    db_session.commit()
    svc = TradeIdeaService(db_session)
    confirmed = svc.confirm_idea(idea.id)
    assert confirmed.status == "confirmed"
    executed = svc.execute_idea(idea.id)
    assert executed.status == "executed"
