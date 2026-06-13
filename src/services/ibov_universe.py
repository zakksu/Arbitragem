"""IBOV Top 20 universe — highest 30-day average volume stocks."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from src.config import PROJECT_ROOT

CSV_PATH = PROJECT_ROOT / "data" / "ibov_top20.csv"


@dataclass
class IBOVSymbol:
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
def load_ibov_top20() -> list[IBOVSymbol]:
    if not CSV_PATH.exists():
        return _fallback_list()
    rows: list[IBOVSymbol] = []
    with CSV_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                IBOVSymbol(
                    symbol=row["symbol"].strip().upper(),
                    name=row.get("name", "").strip(),
                    avg_volume_30d=int(float(row.get("avg_volume_30d", 0))),
                    sector=row.get("sector", "").strip(),
                )
            )
    return rows[:20]


def symbol_list() -> list[str]:
    return [s.symbol for s in load_ibov_top20()]


def _fallback_list() -> list[IBOVSymbol]:
    symbols = [
        ("PETR4", "Petrobras PN", 85_000_000, "Energia"),
        ("VALE3", "Vale ON", 72_000_000, "Mineração"),
        ("ITUB4", "Itaú PN", 65_000_000, "Financeiro"),
        ("BBDC4", "Bradesco PN", 58_000_000, "Financeiro"),
        ("BBAS3", "Banco do Brasil ON", 45_000_000, "Financeiro"),
        ("ABEV3", "Ambev ON", 42_000_000, "Consumo"),
        ("B3SA3", "B3 ON", 38_000_000, "Financeiro"),
        ("WEGE3", "WEG ON", 35_000_000, "Industrial"),
        ("RENT3", "Localiza ON", 32_000_000, "Consumo"),
        ("MGLU3", "Magazine Luiza ON", 30_000_000, "Varejo"),
        ("VIVT3", "Vivo ON", 28_000_000, "Telecom"),
        ("BBSE3", "BB Seguridade ON", 25_000_000, "Financeiro"),
        ("SUZB3", "Suzano ON", 24_000_000, "Papel e Celulose"),
        ("PRIO3", "PetroRio ON", 22_000_000, "Energia"),
        ("RADL3", "Raia Drogasil ON", 20_000_000, "Saúde"),
        ("JBSS3", "JBS ON", 19_000_000, "Consumo"),
        ("BPAC11", "BTG Pactual UNIT", 18_000_000, "Financeiro"),
        ("EQTL3", "Equatorial ON", 17_000_000, "Utilidade Pública"),
        ("GGBR4", "Gerdau PN", 16_000_000, "Siderurgia"),
        ("BOVA11", "iShares IBOV ETF", 15_000_000, "ETF"),
    ]
    return [IBOVSymbol(*s) for s in symbols]
