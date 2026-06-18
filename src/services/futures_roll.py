"""B3 mini futures front-month resolver (11.0 A11.17)."""

from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo

_B3_TZ = ZoneInfo("America/Sao_Paulo")

# B3 contract month codes (futures)
_MONTH_CODE = "FGHJKMNQUVXZ"


def b3_month_code(d: date) -> str:
    return _MONTH_CODE[d.month - 1]


def resolve_front_contract(root: str, ref: date | None = None) -> str:
    """Map WIN/WDO root to active series ticker (e.g. WINM26)."""
    r = root.strip().upper()
    if r.endswith("FUT"):
        r = r[:-3]
    if r not in ("WIN", "WDO", "BIT", "MBR"):
        return root.upper()

    today = ref or datetime.now(_B3_TZ).date()
    year = today.year
    month = today.month
    # Roll to next month in last week of expiry month (simplified: day >= 25)
    if today.day >= 25:
        month += 1
        if month > 12:
            month = 1
            year += 1
    code = b3_month_code(date(year, month, 1))
    yy = year % 100
    return f"{r}{code}{yy:02d}"


@lru_cache
def win_front_symbol(ref_iso: str | None = None) -> str:
    ref = date.fromisoformat(ref_iso) if ref_iso else None
    return resolve_front_contract("WIN", ref)


@lru_cache
def wdo_front_symbol(ref_iso: str | None = None) -> str:
    ref = date.fromisoformat(ref_iso) if ref_iso else None
    return resolve_front_contract("WDO", ref)


def resolve_futures_quote_symbol(symbol: str) -> dict[str, Any]:
    """Resolve generic WINFUT/WDOFUT to front month for quotes."""
    sym = symbol.strip().upper()
    if sym == "WINFUT":
        front = win_front_symbol()
        return {"requested": sym, "resolved": front, "root": "WIN"}
    if sym == "WDOFUT":
        front = wdo_front_symbol()
        return {"requested": sym, "resolved": front, "root": "WDO"}
    return {"requested": sym, "resolved": sym, "root": sym[:3] if len(sym) >= 3 else sym}
