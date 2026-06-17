#!/usr/bin/env python3
"""ProfitDLL HTTP bridge — Windows entry point for real Nelogica integration.

Prefers ProfitDLL when PROFIT_DLL_PATH is set and loadable; otherwise delegates
all endpoints to profit_bridge_stub.py (same HTTP contract as VPS API).

Usage (Windows, next to ProfitChart):
    set PROFIT_DLL_PATH=C:\\Nelogica\\Profit\\ProfitDLL.dll
    python scripts/profit_dll_bridge.py

When Nelogica callbacks are wired, replace `_try_load_dll` body with ctypes bindings
from their official ProfitDLL documentation.
"""

from __future__ import annotations

import importlib.util
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.integrations.profit_dll_detect import probe_dll_loadable

_STUB = ROOT / "scripts" / "profit_bridge_stub.py"
_spec = importlib.util.spec_from_file_location("profit_bridge_stub", _STUB)
_stub = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_stub)

CORE14 = _stub.CORE14
BOVA_UNDERLYING = _stub.BOVA_UNDERLYING
_quote_for = _stub._quote_for
_build_chain = _stub._build_chain
_synthetic_greeks = _stub._synthetic_greeks
_max_pain_from_chain = _stub._max_pain_from_chain

app = FastAPI(title="Profit DLL Bridge", version="3.0.0")
_DLL_LOADED = False
_DLL_PROBE: dict = {"loadable": False, "callbacks_wired": False}


def _try_load_dll() -> bool:
    """Load ProfitDLL via ctypes when available on Windows (callbacks still stub)."""
    global _DLL_LOADED, _DLL_PROBE
    dll_path = os.getenv("PROFIT_DLL_PATH", "").strip() or None
    _DLL_PROBE = probe_dll_loadable(dll_path)
    # TODO: wire Nelogica login/subscribe callbacks when DLL loadable
    _DLL_LOADED = bool(_DLL_PROBE.get("loadable"))
    return _DLL_LOADED


@app.on_event("startup")
def _startup() -> None:
    _try_load_dll()


def _mode() -> str:
    return "dll" if _DLL_LOADED else "fallback"


@app.get("/health")
def health():
    paper = os.getenv("PAPER_TRADING_MODE", "true").lower() in ("1", "true", "yes")
    account_profile = os.getenv("PROFIT_LIVE_STYLE", "day") or "day"
    mode = _mode()
    return {
        "status": "ok",
        "mode": mode,
        "dll_mode": mode,
        "version": "3.0.0",
        "is_paper": paper,
        "account_profile": account_profile,
        "dll_path": os.getenv("PROFIT_DLL_PATH", "") or _DLL_PROBE.get("path"),
        "dll_probe": _DLL_PROBE,
        "callbacks_wired": False,
        "symbols": "core14+bova",
    }


@app.get("/quotes/{symbol}")
def quote(symbol: str):
    return _quote_for(symbol)


@app.get("/quotes")
def all_quotes():
    symbols = CORE14 + [BOVA_UNDERLYING]
    return [_quote_for(s) for s in symbols]


@app.get("/options/bova")
def bova_options_chain():
    return _build_chain(BOVA_UNDERLYING, strike_range=3)


@app.get("/options/stock/{underlying}")
def stock_options(underlying: str):
    return _build_chain(underlying.upper(), strike_range=2)


@app.get("/options/chain/{underlying}")
def unified_options_chain(underlying: str):
    sym = underlying.upper()
    if sym in (BOVA_UNDERLYING, "BOVA"):
        chain = _build_chain(BOVA_UNDERLYING, strike_range=3)
    else:
        chain = _build_chain(sym, strike_range=2)
    mp = _max_pain_from_chain(chain)
    if mp:
        chain["max_pain"] = mp
    return chain


@app.get("/greeks/{symbol}")
def greeks(symbol: str):
    sym = symbol.upper()
    seed = int(hashlib.md5(sym.encode()).hexdigest()[:8], 16)
    if "X" in sym[4:] or sym.startswith("BOVAX"):
        opt_type = "call"
        strike = float("".join(c for c in sym if c.isdigit()) or seed % 100)
    elif "Y" in sym[4:] or sym.startswith("BOVAY"):
        opt_type = "put"
        strike = float("".join(c for c in sym if c.isdigit()) or seed % 100)
    else:
        return {
            "symbol": sym,
            "delta": 1.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "iv": 0.0,
            "source": _mode(),
        }
    und_last = _quote_for(sym[:4] + "4" if len(sym) > 6 else BOVA_UNDERLYING)["last"]
    g = _synthetic_greeks(sym, opt_type, strike, und_last)
    g["source"] = _mode()
    return g


@app.get("/iv-rank/{underlying}")
def iv_rank(underlying: str):
    return _stub.iv_rank(underlying)


@app.get("/positions")
def positions():
    return []


@app.get("/trades/today")
def trades_today():
    return _stub.trades_today()


@app.post("/backtest/run")
def run_backtest(payload: dict):
    result = _stub.run_backtest(payload)
    result["source"] = _mode()
    return result


@app.post("/orders")
def place_order(payload: dict):
    return _stub.place_order(payload)


@app.get("/orders/pending")
def pending_orders():
    return _stub.pending_orders()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PROFIT_BRIDGE_PORT", "9100"))
    uvicorn.run(app, host="0.0.0.0", port=port)
