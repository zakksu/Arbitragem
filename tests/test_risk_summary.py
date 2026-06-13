"""Risk summary API tests."""

import pytest

from src.config import get_settings
from src.models import get_session_factory, init_db
from src.services.risk_summary import build_risk_summary


@pytest.fixture
def db_session():
    get_settings.cache_clear()
    init_db()
    session = get_session_factory()()
    yield session
    session.close()


def test_risk_summary_shape(db_session):
    summary = build_risk_summary(db_session)
    assert "day_pnl" in summary
    assert "paper_trading_mode" in summary
    assert summary["status"] in ("ok", "warning", "blocked")
    assert summary["tightest_loss_limit_brl"] > 0
