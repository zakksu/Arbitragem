"""Profit account profile resolution."""

from src.config import get_settings
from src.services.profit_accounts import resolve_profit_account


def test_paper_uses_simulator():
    get_settings.cache_clear()
    import os

    os.environ["PAPER_TRADING_MODE"] = "true"
    get_settings.cache_clear()
    acct = resolve_profit_account()
    assert acct["profile"] == "sim"
    assert acct["account_id"] == "3368"
    assert acct["is_paper"] is True


def test_live_day_trade():
    get_settings.cache_clear()
    import os

    os.environ["PAPER_TRADING_MODE"] = "false"
    os.environ["PROFIT_LIVE_STYLE"] = "day"
    get_settings.cache_clear()
    acct = resolve_profit_account()
    assert acct["profile"] == "day"
    assert acct["label"] == "Clear - DayTrade"
    assert acct["is_paper"] is False


def test_live_swing_trade():
    get_settings.cache_clear()
    import os

    os.environ["PAPER_TRADING_MODE"] = "false"
    os.environ["PROFIT_LIVE_STYLE"] = "swing"
    get_settings.cache_clear()
    acct = resolve_profit_account()
    assert acct["profile"] == "swing"
