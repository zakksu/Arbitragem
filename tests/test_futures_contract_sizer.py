"""Futures contract sizer tests."""

from __future__ import annotations

from src.services.futures_contract_sizer import max_futures_contracts


def test_small_account_one_win_contract():
    r = max_futures_contracts("WINJ26", capital_brl=500)
    assert r["is_futures"] is True
    assert r["max_contracts"] == 1
    assert r["recommended_contracts"] == 1


def test_larger_account_caps_by_margin():
    r = max_futures_contracts("WDOF26", capital_brl=5000)
    assert r["is_futures"] is True
    assert r["max_contracts"] >= 1


def test_equity_not_futures():
    r = max_futures_contracts("PETR4", capital_brl=500)
    assert r["is_futures"] is False
