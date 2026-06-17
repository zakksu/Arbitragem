"""Tests for trading sleeves — per-market ON/OFF gates."""

from __future__ import annotations

import pytest

from src.services.kill_switch import is_active, set_active, status as kill_status
from src.services.trading_sleeves import (
    SLEEVES,
    ensure_sleeve_open,
    set_all,
    set_sleeve,
    sleeve_for_idea,
    status,
)


@pytest.fixture(autouse=True)
def reset_sleeves():
    set_all(True)
    yield
    set_all(True)


def test_sleeve_mapping_scalp_is_cash():
    idea = {"structure_type": "scalp", "legs": [{"symbol": "PETR4", "side": "buy"}]}
    assert sleeve_for_idea(idea) == "cash"


def test_sleeve_mapping_pair():
    idea = {
        "structure_type": "pair_relative",
        "rationale_tags": ["sector_pair"],
        "legs": [{"symbol": "PETR4"}, {"symbol": "PRIO3"}],
    }
    assert sleeve_for_idea(idea) == "pairs"


def test_sleeve_mapping_options():
    idea = {
        "structure_type": "vertical",
        "legs": [{"symbol": "PETR4"}, {"symbol": "PETRA150"}],
    }
    assert sleeve_for_idea(idea) == "options"


def test_pause_sleeve_blocks_action():
    set_sleeve("cash", False, reason="test pause")
    with pytest.raises(ValueError, match="CASH sleeve paused"):
        ensure_sleeve_open("cash", "confirm")


def test_kill_switch_shim_pauses_all():
    set_active(True, reason="legacy kill")
    assert is_active() is True
    st = status()
    assert st["all_open"] is False
    assert all(not st["sleeves"][s] for s in SLEEVES)


def test_resume_all_sleeves():
    set_active(True)
    set_active(False)
    assert is_active() is False
    assert status()["all_open"] is True


def test_kill_status_includes_sleeves():
    set_sleeve("options", False)
    ks = kill_status()
    assert ks["active"] is True
    assert ks["sleeves"]["options"] is False
