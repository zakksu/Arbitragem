"""Hard conflict blocks confirm — 10.0 / 12.0."""

from __future__ import annotations

import pytest

from src.config import get_settings
from src.models import TradeIdea, get_session_factory, init_db
from src.services.trade_ideas import TradeIdeaService


@pytest.fixture
def db_session(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'conflict.db'}")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    get_settings.cache_clear()
    init_db()
    session = get_session_factory()()
    yield session
    session.close()


def test_confirm_idea_raises_on_hard_conflict(db_session):
    idea = TradeIdea(
        symbol="PETR4",
        structure_type="scalp_long",
        side="long",
        status="detected",
        entry_price=38.0,
        backtest_proof={"profit_factor": 1.5, "max_drawdown_pct": 5.0},
        meta={
            "decision_brief": {
                "bullets": [
                    "Take the trade — add to loser on dip",
                    "Entry at VWAP",
                    "Stop 4 ticks",
                    "Target 6 ticks",
                    "Risk small",
                ],
                "conflicts": [],
            }
        },
    )
    db_session.add(idea)
    db_session.commit()

    svc = TradeIdeaService(db_session)
    with pytest.raises(ValueError, match="averaging-down|prohibited|conflict"):
        svc.confirm_idea(idea.id)
