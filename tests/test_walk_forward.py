"""Tests for walk-forward, risk checks, and strategy updates."""

import pytest

from src.config import get_settings
from src.models import Strategy, StrategyStatus, get_session_factory, init_db
from src.services.risk_manager import RiskManager
from src.services.strategy_manager import StrategyService
from src.services.walk_forward import WalkForwardOptimizer


@pytest.fixture
def db_session():
    get_settings.cache_clear()
    init_db()
    session = get_session_factory()()
    yield session
    session.close()


def test_check_can_start_ok(db_session):
    strategy = StrategyService(db_session).get_or_create_sample()
    result = RiskManager(db_session).check_can_start(strategy)
    assert result.allowed is True


def test_walk_forward_completes(db_session):
    strategy = StrategyService(db_session).get_or_create_sample()
    run = WalkForwardOptimizer(db_session).run(
        strategy,
        "BOVAX125",
        {"stop_ticks": [3, 5], "target_ticks": [6, 8]},
        folds=2,
    )
    assert run.status == "completed"
    assert run.best_parameters is not None
    assert run.results is not None
    assert "folds" in run.results


def test_update_strategy_ntsl(db_session):
    svc = StrategyService(db_session)
    strategy = svc.get_or_create_sample()
    updated = svc.update_strategy(
        strategy.id,
        {"description": "Updated desc", "ntsl_code": "// new code"},
    )
    assert updated.description == "Updated desc"
    assert updated.ntsl_code == "// new code"


def test_pause_strategy(db_session):
    svc = StrategyService(db_session)
    strategy = svc.get_or_create_sample()
    svc.start_strategy(strategy.id)
    paused = svc.pause_strategy(strategy.id)
    assert paused.status == StrategyStatus.PAUSED.value


def test_python_backtest_bridge_candles(monkeypatch, db_session):
    from src.services.backtest import BacktestService

    monkeypatch.setenv("WALK_FORWARD_USE_BRIDGE_CANDLES", "true")
    get_settings.cache_clear()

    class _Client:
        def is_available(self):
            return True

        def get_session_candles(self, _sym):
            return [{"close": 10.0 + i * 0.1, "volume": 100} for i in range(20)]

    monkeypatch.setattr(
        "src.services.backtest.get_profit_client",
        lambda: _Client(),
    )
    strategy = StrategyService(db_session).get_or_create_sample()
    run = BacktestService(db_session).run_python_backtest(strategy, "PETR4", bars=10)
    assert run.metrics.get("data_source") == "bridge_candles"
