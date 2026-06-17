"""Trading orchestrator + idea levels."""

from datetime import datetime

from src.services.idea_levels import enrich_idea_levels, idea_risk_summary
from src.services.trading_orchestrator import orchestrator_should_run


def test_enrich_levels_from_quote(monkeypatch):
    from datetime import datetime as dt

    from src.integrations.profit_bridge import ProfitQuote

    class FakeClient:
        def get_quote(self, symbol):
            return ProfitQuote(
                symbol=symbol,
                bid=57.0,
                ask=57.02,
                last=57.01,
                volume=1000,
                timestamp=dt.utcnow(),
            )

    monkeypatch.setattr("src.services.idea_levels.get_profit_client", lambda: FakeClient())
    idea = {"symbol": "VALE3", "side": "long", "stop_ticks": 5, "target_ticks": 8}
    out = enrich_idea_levels(idea)
    assert out["entry_price"] == 57.01
    assert out["stop_price"] < out["entry_price"]
    assert out["target_price"] > out["entry_price"]


def test_risk_summary():
    idea = {"entry_price": 10.0, "stop_price": 9.5, "target_price": 11.0, "side": "long"}
    r = idea_risk_summary(idea, quantity=100)
    assert r["risk_brl"] == 50.0
    assert r["reward_brl"] == 100.0
    assert r["risk_reward"] == 2.0


def test_orchestrator_b3_session_0930():
    from src.services.trading_orchestrator import b3_session_open

    class FakeDatetime(datetime):
        @classmethod
        def utcnow(cls):
            # Tuesday 12:30 UTC = 09:30 BRT
            return cls(2026, 6, 16, 12, 30)

    import src.services.trading_orchestrator as orch

    orig = orch.datetime
    orch.datetime = FakeDatetime
    try:
        assert b3_session_open() is True
    finally:
        orch.datetime = orig


def test_orchestrator_active_in_paper(monkeypatch):
    monkeypatch.setenv("PAPER_TRADING_MODE", "true")
    monkeypatch.setenv("AUTO_TRADING_ON_SLEEVES", "true")
    from src.config import get_settings
    from src.services.trading_sleeves import set_all

    get_settings.cache_clear()
    set_all(True)
    assert orchestrator_should_run() is True
