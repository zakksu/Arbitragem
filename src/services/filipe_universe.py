"""Filipe Core14 — liquid IBOV blue chips for 2.0 blackboard."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from src.config import PROJECT_ROOT

CSV_PATH = PROJECT_ROOT / "data" / "filipe_core14.csv"
CORE5_CSV_PATH = PROJECT_ROOT / "data" / "filipe_core5.csv"
CORE5_STOCKS = ("PETR4", "VALE3", "ITUB4", "BOVA11", "PRIO3")

SECTOR_BASKETS: dict[str, list[str]] = {
    "banks": ["ITUB4", "BBAS3", "BBDC4", "BBSE3", "B3SA3"],
    "steel": ["GGBR4", "CSNA3", "USIM5"],
    "energy": ["PETR4", "PRIO3"],
    "defensive": ["ABEV3", "SUZB3", "WEGE3"],
}

BOVA_UNDERLYING = "BOVA11"


@dataclass
class CoreSymbol:
    symbol: str
    name: str
    avg_volume_30d: int
    sector: str = ""

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "avg_volume_30d": self.avg_volume_30d,
            "sector": self.sector,
        }


@lru_cache
def load_filipe_core14() -> list[CoreSymbol]:
    if not CSV_PATH.exists():
        return _fallback()
    rows: list[CoreSymbol] = []
    with CSV_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(
                CoreSymbol(
                    symbol=row["symbol"].strip().upper(),
                    name=row.get("name", "").strip(),
                    avg_volume_30d=int(float(row.get("avg_volume_30d", 0))),
                    sector=row.get("sector", "").strip(),
                )
            )
    return rows[:14]


@lru_cache
def load_filipe_core5() -> list[CoreSymbol]:
    if not CORE5_CSV_PATH.exists():
        return [s for s in _fallback() if s.symbol in CORE5_STOCKS]
    rows: list[CoreSymbol] = []
    with CORE5_CSV_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(
                CoreSymbol(
                    symbol=row["symbol"].strip().upper(),
                    name=row.get("name", "").strip(),
                    avg_volume_30d=int(float(row.get("avg_volume_30d", 0))),
                    sector=row.get("sector", "").strip(),
                )
            )
    return rows[:5]


def core5_symbol_list() -> list[str]:
    return [s.symbol for s in load_filipe_core5()]


def symbol_list() -> list[str]:
    return [s.symbol for s in load_filipe_core14()]


def sector_for(symbol: str) -> str | None:
    sym = symbol.upper()
    for s in load_filipe_core14():
        if s.symbol == sym:
            return s.sector or None
    return None


def _fallback() -> list[CoreSymbol]:
    return [
        CoreSymbol("PETR4", "Petrobras PN", 85_000_000, "Energia"),
        CoreSymbol("VALE3", "Vale ON", 72_000_000, "Mineração"),
        CoreSymbol("PRIO3", "PetroRio ON", 22_000_000, "Energia"),
        CoreSymbol("ITUB4", "Itaú PN", 65_000_000, "Financeiro"),
        CoreSymbol("BBAS3", "Banco do Brasil ON", 45_000_000, "Financeiro"),
        CoreSymbol("BBDC4", "Bradesco PN", 58_000_000, "Financeiro"),
        CoreSymbol("BBSE3", "BB Seguridade ON", 25_000_000, "Financeiro"),
        CoreSymbol("B3SA3", "B3 ON", 38_000_000, "Financeiro"),
        CoreSymbol("ABEV3", "Ambev ON", 42_000_000, "Consumo"),
        CoreSymbol("GGBR4", "Gerdau PN", 16_000_000, "Siderurgia"),
        CoreSymbol("CSNA3", "Siderúrgica Nacional ON", 12_000_000, "Siderurgia"),
        CoreSymbol("USIM5", "Usiminas PNA", 9_000_000, "Siderurgia"),
        CoreSymbol("SUZB3", "Suzano ON", 24_000_000, "Papel"),
        CoreSymbol("WEGE3", "WEG ON", 35_000_000, "Industrial"),
    ]
