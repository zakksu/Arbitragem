"""Delta-aware BOVA11 hedge sizing vs Core14 basket (3.0 GA)."""

from __future__ import annotations

import hashlib

from src.integrations.profit_bridge import get_profit_client
from src.services.filipe_universe import SECTOR_BASKETS, load_filipe_core14

# Stub betas vs IBOV (BOVA11 proxy)
_STUB_BETAS: dict[str, float] = {
    "PETR4": 1.15,
    "VALE3": 1.05,
    "PRIO3": 1.2,
    "ITUB4": 0.85,
    "BBAS3": 0.9,
    "BBDC4": 0.88,
    "BBSE3": 0.75,
    "B3SA3": 0.95,
    "ABEV3": 0.6,
    "GGBR4": 1.1,
    "CSNA3": 1.25,
    "USIM5": 1.3,
    "SUZB3": 0.7,
    "WEGE3": 0.8,
}


def _symbol_seed(symbol: str) -> int:
    return int(hashlib.md5(symbol.upper().encode()).hexdigest()[:8], 16)


def basket_beta(symbols: list[str] | None = None) -> float:
    """Weighted average beta of basket vs BOVA11."""
    if not symbols:
        symbols = [s.symbol for s in load_filipe_core14()]
    if not symbols:
        return 1.0
    betas = [_STUB_BETAS.get(s, 0.9 + (_symbol_seed(s) % 30) / 100.0) for s in symbols]
    return round(sum(betas) / len(betas), 3)


def suggest_bova_hedge(
    cash_symbol: str,
    cash_qty: int = 100,
    *,
    target_delta_neutral: bool = True,
) -> dict:
    """
    Suggest BOVA put contracts to hedge long cash exposure.
    Uses stub beta + bridge greeks when available.
    """
    sym = cash_symbol.upper()
    client = get_profit_client()
    beta = _STUB_BETAS.get(sym, basket_beta([sym]))
    cash_delta = round(beta * cash_qty / 100.0, 3)

    bova_chain = client.get_option_chain("BOVA11")
    puts = bova_chain.get("puts") or []
    atm_put = puts[len(puts) // 2] if puts else None
    put_delta = -0.35
    if atm_put:
        greeks = client.get_greeks(atm_put["symbol"])
        put_delta = float(greeks.get("delta", -0.35))

    if target_delta_neutral and put_delta != 0:
        bova_qty = max(1, int(round(abs(cash_delta / put_delta))))
    else:
        bova_qty = max(1, int(round(cash_qty * beta / 200)))

    return {
        "cash_symbol": sym,
        "cash_qty": cash_qty,
        "cash_beta": beta,
        "cash_delta_est": cash_delta,
        "bova_underlying": "BOVA11",
        "bova_put_symbol": atm_put["symbol"] if atm_put else "BOVAY",
        "bova_put_strike": atm_put.get("strike") if atm_put else None,
        "bova_put_qty": bova_qty,
        "put_delta_est": put_delta,
        "hedge_ratio": round(bova_qty / max(cash_qty / 100, 1), 2),
        "source": "stub",
    }


def apply_bova_sizing_to_legs(legs: list[dict], cash_symbol: str) -> list[dict]:
    """Patch bova_hedge legs with delta-aware BOVA quantity."""
    hedge = suggest_bova_hedge(cash_symbol)
    out: list[dict] = []
    for leg in legs:
        leg = dict(leg)
        if leg.get("leg_type") in ("bova_put", "bova_call"):
            leg["quantity"] = hedge["bova_put_qty"]
            leg["hedge_ratio"] = hedge["hedge_ratio"]
        out.append(leg)
    return out
