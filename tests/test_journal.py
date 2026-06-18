"""Journal sync from Clear + Profit."""

import pytest

from src.config import get_settings
from src.models import Trade, get_session_factory, init_db
from src.services.journal import JournalService


@pytest.fixture
def db_session():
    get_settings.cache_clear()
    init_db()
    session = get_session_factory()()
    yield session
    session.close()


def test_sync_all_sources_returns_breakdown(db_session, monkeypatch):
  from src.integrations.profit_bridge import ProfitTrade
  from datetime import datetime
  import uuid

  ext = f"test-{uuid.uuid4().hex[:8]}"

  class FakeProfit:
      def get_trades_today(self):
          return [
              ProfitTrade(
                  external_id=ext,
                  symbol="PETR4",
                  side="buy",
                  quantity=100,
                  price=10.0,
                  fees=0,
                  pnl=None,
                  executed_at=datetime.utcnow(),
                  raw={},
              )
          ]

  class FakeClear:
      def is_configured(self):
          return False

      def get_trades_today(self):
          return []

  monkeypatch.setattr(
      "src.services.journal.JournalService.auto_analyze_recent_trades",
      lambda self, limit=10: 0,
  )

  svc = JournalService(db_session)
  svc.profit = FakeProfit()
  svc.clear = FakeClear()
  result = svc.sync_all_sources()
  assert result["imported_profit"] == 1
  assert result["imported_clear"] == 0
  assert result["clear_configured"] is False
  assert (
      db_session.query(Trade).filter(Trade.external_id == f"profit-{ext}").count() == 1
  )
