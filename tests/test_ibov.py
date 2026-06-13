"""Tests for IBOV universe and scalp patterns."""

from src.services.ibov_universe import load_ibov_top20, symbol_list
from src.services.scalp_patterns import analyze_scalp


def test_bova_option_metrics():
    from src.services.scanner import _bova_option_metrics

    oi, skew = _bova_option_metrics("BOVAX125", 1_000_000)
    assert oi is not None and oi > 0
    assert skew is not None
    assert _bova_option_metrics("PETR4", 1_000_000) == (None, None)


def test_ibov_top20_count():
    symbols = load_ibov_top20()
    assert len(symbols) == 20
    assert symbols[0].symbol == "PETR4"
    assert "BOVA11" in symbol_list()


def test_scalp_long_bias():
    signal = analyze_scalp(
        volume=1_000_000,
        spike_score=75,
        price_change_pct=0.8,
        spread=0.02,
        min_volume=5000,
        avg_volume_30d=50_000_000,
    )
    assert signal.side_bias == "long"
    assert signal.reliability >= 40
    assert "scalp_long" in signal.pattern_tags


def test_quotes_batch_unique_volumes():
    from src.config import get_settings
    from src.integrations.profit_bridge import ProfitBridgeClient

    get_settings.cache_clear()
    client = ProfitBridgeClient()
    batch = client.get_quotes_batch(["PETR4", "VALE3", "ITUB4"])
    assert len(batch) == 3
    volumes = {batch[s].volume for s in batch}
    assert len(volumes) == 3


def test_scalp_short_bias():
    signal = analyze_scalp(
        volume=900_000,
        spike_score=70,
        price_change_pct=-0.9,
        spread=0.02,
        min_volume=5000,
        avg_volume_30d=40_000_000,
    )
    assert signal.side_bias == "short"
    assert "scalp_short" in signal.pattern_tags
