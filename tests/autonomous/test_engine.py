"""Autonomous engine + risk guardian tests."""

from src.autonomous.engine import AutonomousEngine
from src.autonomous.risk_guardian import RiskGuardian
from src.services.trading_sleeves import set_all


def test_risk_guardian_allows_when_sleeves_open(db_session, monkeypatch):
    monkeypatch.setenv("PAPER_TRADING_MODE", "true")
    from src.config import get_settings

    get_settings.cache_clear()
    set_all(True)
    ok, reason = RiskGuardian(db_session).can_run_autonomous()
    assert ok is True
    assert reason is None


def test_autonomous_daily_routine_runs(db_session, monkeypatch):
    monkeypatch.setenv("PAPER_TRADING_MODE", "true")
    monkeypatch.setenv("WALK_FORWARD_AUTO_PROMOTE", "false")
    from src.config import get_settings

    get_settings.cache_clear()
    set_all(True)
    result = AutonomousEngine(db_session).run_daily_routine_sync()
    assert result.risk_blocked is False
    assert isinstance(result.to_dict(), dict)
