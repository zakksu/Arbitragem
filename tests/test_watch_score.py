"""Tests for watchlist composite score."""

from __future__ import annotations

from src.services.idea_score import score_idea
from src.services.watch_score import score_watchlist_row


def test_watch_score_penalizes_wide_spread():
    quote = {"last": 100.0, "bid": 99.0, "ask": 100.5}
    high = score_watchlist_row("PETR4", quote, None, 80, cost_brl=50.0)
    tight = score_watchlist_row(
        "PETR4", {"last": 100.0, "bid": 99.95, "ask": 100.05}, None, 80, cost_brl=50.0
    )
    assert tight > high


def test_watch_score_sector_penalty():
    base = score_watchlist_row("PETR4", {"last": 38.0}, None, 70, sector_corr_penalty=0)
    penalized = score_watchlist_row("PETR4", {"last": 38.0}, None, 70, sector_corr_penalty=12)
    assert penalized < base


def test_idea_score_penalizes_high_dd():
    idea = {
        "reliability": 80,
        "backtest_proof": {"profit_factor": 1.5, "max_drawdown_pct": 20.0},
        "status": "backtested",
    }
    good = score_idea({**idea, "backtest_proof": {"profit_factor": 1.5, "max_drawdown_pct": 5.0}})
    bad = score_idea(idea)
    assert bad < good


def test_idea_score_walk_forward_bonus():
    base = {"reliability": 70, "status": "detected", "backtest_proof": {"profit_factor": 1.4}}
    with_wf = {**base, "walk_forward_pass": True}
    without_wf = {**base, "walk_forward_pass": False}
    assert score_idea(with_wf) > score_idea(without_wf)
