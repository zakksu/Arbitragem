"""Basic tests for MVP services."""

import pytest

from src.config import get_settings
from src.models import Strategy, get_session_factory, init_db
from src.services.backtest import BacktestService
from src.services.optimizer import OptimizerService
from src.services.risk_manager import RiskManager
from src.services.strategy_manager import StrategyService


@pytest.fixture
def db_session():
    get_settings.cache_clear()
    init_db()
    session = get_session_factory()()
    yield session
    session.close()


def test_create_sample_strategy(db_session):
    strategy = StrategyService(db_session).get_or_create_sample()
    assert strategy.name == "BOVA Scalp MVP"
    assert strategy.ntsl_code is not None


def test_python_backtest(db_session):
    strategy = StrategyService(db_session).get_or_create_sample()
    run = BacktestService(db_session).run_python_backtest(strategy, "BOVAX125", bars=100)
    assert run.metrics is not None
    assert "net_pnl" in run.metrics


def test_grid_search(db_session):
    strategy = StrategyService(db_session).get_or_create_sample()
    run = OptimizerService(db_session).run_grid_search(
        strategy,
        "BOVAX125",
        {"stop_ticks": [3, 5], "target_ticks": [6, 8]},
    )
    assert run.status == "completed"
    assert run.best_parameters is not None


def test_risk_manager_blocks_inactive(db_session):
    strategy = StrategyService(db_session).get_or_create_sample()
    rm = RiskManager(db_session)
    result = rm.check_strategy_order(strategy, "BOVAX125", 1, 0)
    assert result.allowed is False
