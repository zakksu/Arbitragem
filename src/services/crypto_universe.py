"""Crypto watch universe — BTC/ETH/SOL (4.2 A4.23, watch-only)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class CryptoSymbol:
    symbol: str
    name: str
    binance_pair: str
    quote_currency: str = "USDT"

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "binance_pair": self.binance_pair,
            "quote_currency": self.quote_currency,
            "asset_class": "crypto",
            "read_only": True,
            "auto_trade": False,
        }


@lru_cache
def load_crypto_universe() -> list[CryptoSymbol]:
    return [
        CryptoSymbol("BTC", "Bitcoin", "BTCUSDT"),
        CryptoSymbol("ETH", "Ethereum", "ETHUSDT"),
        CryptoSymbol("SOL", "Solana", "SOLUSDT"),
    ]


def symbol_list() -> list[str]:
    return [c.symbol for c in load_crypto_universe()]


def is_crypto(symbol: str) -> bool:
    return symbol.upper() in set(symbol_list())


def binance_pair_for(symbol: str) -> str | None:
    sym = symbol.upper()
    for c in load_crypto_universe():
        if c.symbol == sym:
            return c.binance_pair
    return None
