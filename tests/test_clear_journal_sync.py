"""Clear journal sync — skip mock pollution when CLEAR_API_KEY unset (A12.8)."""

from datetime import datetime

import pytest

from src.config import get_settings
from src.integrations.clear_api import ClearTrade
from src.models import Trade, get_session_factory, init_db
from src.services.journal import JournalService


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'clear_sync.db'}")
    get_settings.cache_clear()
    init_db()
    session = get_session_factory()()
    yield session
    session.close()


def test_unconfigured_clear_skips_mock_trades(db_session, monkeypatch):
    monkeypatch.delenv("CLEAR_API_KEY", raising=False)
    get_settings.cache_clear()

    svc = JournalService(db_session)
    assert svc.clear.is_configured() is False

    imported = svc.sync_trades_from_clear()
    assert imported == 0
    assert db_session.query(Trade).filter(Trade.source == "clear").count() == 0

    result = svc.sync_all_sources(analyze=False)
    assert result["clear_configured"] is False
    assert result["imported_clear"] == 0


def test_configured_clear_imports_trades(db_session, monkeypatch):
    monkeypatch.setenv("CLEAR_API_KEY", "test-key")
    get_settings.cache_clear()

    now = datetime.utcnow()

    class FakeClear:
        def is_configured(self) -> bool:
            return True

        def get_trades_today(self):
            return [
                ClearTrade(
                    external_id="CLEAR-T-001",
                    symbol="PETR4",
                    side="buy",
                    quantity=100,
                    price=38.0,
                    fees=2.5,
                    executed_at=now,
                    raw={"id": "CLEAR-T-001"},
                )
            ]

    class FakeProfit:
        def get_trades_today(self):
            return []

    svc = JournalService(db_session)
    svc.clear = FakeClear()
    svc.profit = FakeProfit()

    result = svc.sync_all_sources(analyze=False)
    assert result["clear_configured"] is True
    assert result["imported_clear"] == 1
    assert (
        db_session.query(Trade)
        .filter(Trade.external_id == "CLEAR-T-001", Trade.source == "clear")
        .count()
        == 1
    )
