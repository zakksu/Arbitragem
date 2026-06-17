"""B3 mini futures universe — WIN/WDO (4.1 A4.20)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class FutureSymbol:
    symbol: str
    name: str
    underlying: str
    tick_size: float
    contract_currency: str
    session: str = "b3_day"

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "underlying": self.underlying,
            "tick_size": self.tick_size,
            "contract_currency": self.contract_currency,
            "session": self.session,
            "asset_class": "future",
        }


@lru_cache
def load_futures_universe() -> list[FutureSymbol]:
    return [
        FutureSymbol(
            symbol="WINFUT",
            name="Mini Ibovespa",
            underlying="IBOV",
            tick_size=5.0,
            contract_currency="BRL",
            session="b3_day",
        ),
        FutureSymbol(
            symbol="WDOFUT",
            name="Mini Dollar",
            underlying="USD/BRL",
            tick_size=0.5,
            contract_currency="BRL",
            session="b3_day",
        ),
    ]


def symbol_list() -> list[str]:
    return [f.symbol for f in load_futures_universe()]


def is_future(symbol: str) -> bool:
    return symbol.upper() in set(symbol_list())
