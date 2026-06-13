"""Filipe Core14 universe tests (2.0)."""

from src.services.filipe_universe import SECTOR_BASKETS, load_filipe_core14, symbol_list


def test_core14_count():
    symbols = load_filipe_core14()
    assert len(symbols) == 14
    assert symbols[0].symbol == "PETR4"
    assert "WEGE3" in symbol_list()


def test_sector_baskets():
    assert len(SECTOR_BASKETS["banks"]) == 5
    assert "PETR4" in SECTOR_BASKETS["energy"]
    assert "GGBR4" in SECTOR_BASKETS["steel"]
