"""Tests for ProfitChart CSV parser."""

from pathlib import Path

import pytest

from src.integrations.profit_parser import parse_profit_backtest_csv
from src.models import get_session_factory, init_db
from src.config import get_settings

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def db_session():
    get_settings.cache_clear()
    init_db()
    session = get_session_factory()()
    yield session
    session.close()


def test_parse_trade_list_csv():
    result = parse_profit_backtest_csv(FIXTURES / "profit_backtest_trades.csv")
    assert result.format == "trades"
    assert result.total_trades == 5
    assert result.net_pnl == pytest.approx(130.0)
    assert result.winning_trades == 3
    assert result.losing_trades == 2
    assert result.win_rate == pytest.approx(0.6)
    assert "BOVAX125" in result.symbols
    assert result.max_drawdown > 0
    assert len(result.trades_preview) <= 20


def test_parse_summary_kv_csv():
    result = parse_profit_backtest_csv(FIXTURES / "profit_backtest_summary.csv")
    assert result.format == "summary"
    assert result.total_trades == 85
    assert result.win_rate == pytest.approx(0.5882, rel=1e-3)
    assert result.net_pnl == pytest.approx(1250.50)
    assert result.max_drawdown == pytest.approx(320.0)
    assert result.profit_factor == pytest.approx(1.85)
    d = result.to_dict()
    assert "max_drawdown_pct" in d
    assert d["max_drawdown_pct"] < 100.0


def test_trade_list_dd_pct_not_absurd():
    result = parse_profit_backtest_csv(FIXTURES / "profit_backtest_trades.csv")
    d = result.to_dict()
    if "max_drawdown_pct" in d:
        assert d["max_drawdown_pct"] <= 100.0


def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        parse_profit_backtest_csv(FIXTURES / "missing.csv")


def test_profit_backtest_via_service(db_session, tmp_path):
    from shutil import copy

    from src.services.backtest import BacktestService
    from src.services.strategy_manager import StrategyService

    fixture = FIXTURES / "profit_backtest_trades.csv"
    dest = tmp_path / "profit.csv"
    copy(fixture, dest)

    strategy = StrategyService(db_session).get_or_create_sample()
    run = BacktestService(db_session).run_profit_backtest(strategy, "BOVAX125", dest)
    assert run.metrics is not None
    assert run.metrics.get("total_trades") == 5
    assert run.metrics.get("net_pnl") == pytest.approx(130.0)
