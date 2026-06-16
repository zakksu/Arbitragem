"""Drawdown normalization — 3.0.1 backend DD fix."""

import numpy as np
import pytest

from src.services.metrics_utils import (
    backtest_proof_drawdown_pct,
    equity_drawdown,
    normalize_drawdown_pct,
)


def test_equity_drawdown_from_pnl_series():
    pnls = np.array([30.0, -20.0, 80.0, -20.0])
    max_dd, dd_pct = equity_drawdown(pnls)
    assert max_dd == pytest.approx(20.0)
    assert dd_pct == pytest.approx(20.0 / 30.0 * 100.0)


def test_normalize_fraction_to_percent():
    assert normalize_drawdown_pct(0.058) == pytest.approx(5.8)


def test_normalize_missing_returns_none_not_100():
    assert normalize_drawdown_pct(None) is None


def test_backtest_proof_prefers_explicit_pct():
    assert backtest_proof_drawdown_pct({"max_drawdown_pct": 5.8}) == pytest.approx(5.8)


def test_backtest_proof_absolute_with_peak_hint():
    metrics = {"max_drawdown": 320.0, "net_pnl": 1250.5}
    dd = backtest_proof_drawdown_pct(metrics)
    assert dd is not None
    assert dd < 100.0
