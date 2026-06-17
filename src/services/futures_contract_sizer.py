"""Futures contract sizing — margin-aware caps for small accounts (11.0 / 12.0)."""

from __future__ import annotations

from typing import Any

# B3 day-trade margins (BRL) — conservative defaults; verify with broker.
_MARGIN_BRL: dict[str, float] = {
    "WIN": 155.0,
    "WDO": 140.0,
    "BIT": 45.0,
    "MBR": 65.0,
}


def _futures_root(symbol: str) -> str | None:
    sym = symbol.strip().upper()
    for root in _MARGIN_BRL:
        if sym.startswith(root):
            return root
    return None


def max_futures_contracts(
    symbol: str,
    *,
    capital_brl: float,
    buffer_brl: float = 100.0,
) -> dict[str, Any]:
    """Return max concurrent contracts given capital and margin table."""
    root = _futures_root(symbol)
    if not root:
        return {"symbol": symbol, "is_futures": False, "max_contracts": 0}

    margin = _MARGIN_BRL[root]
    spendable = max(0.0, capital_brl - buffer_brl)
    if margin <= 0:
        return {"symbol": symbol, "is_futures": True, "root": root, "max_contracts": 1}

    max_c = max(1, int(spendable // margin)) if capital_brl >= 2000 else 1
    if capital_brl < 2000:
        max_c = 1

    return {
        "symbol": symbol.strip().upper(),
        "is_futures": True,
        "root": root,
        "margin_brl": margin,
        "capital_brl": capital_brl,
        "max_contracts": max_c,
        "recommended_contracts": min(max_c, 1),
    }
