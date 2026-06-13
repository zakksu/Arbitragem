#!/usr/bin/env python3
"""ProfitDLL HTTP bridge — Windows entry point for real Nelogica integration.

Falls back to synthetic quotes when PROFIT_DLL_PATH is missing or unloadable.
Same HTTP contract as profit_bridge_stub.py so the VPS API needs no changes.

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
_STUB = ROOT / "scripts" / "profit_bridge_stub.py"
_spec = importlib.util.spec_from_file_location("profit_bridge_stub", _STUB)
_stub = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_stub)
IBOV_TOP20 = _stub.IBOV_TOP20
_quote_for = _stub._quote_for

app = FastAPI(title="Profit DLL Bridge", version="1.0.0")
_DLL_LOADED = False


def _try_load_dll() -> bool:
    """Load ProfitDLL via ctypes when available on Windows."""
    global _DLL_LOADED
    dll_path = os.getenv("PROFIT_DLL_PATH", "").strip()
    if not dll_path or not Path(dll_path).exists():
        return False
    if sys.platform != "win32":
        return False
    try:
        import ctypes  # noqa: F401

        # TODO: ctypes.CDLL(dll_path) + Nelogica login/subscribe callbacks
        _DLL_LOADED = False
        return _DLL_LOADED
    except Exception:
        return False


@app.on_event("startup")
def _startup() -> None:
    _try_load_dll()


@app.get("/health")
def health():
    mode = "dll" if _DLL_LOADED else "fallback"
    return {
        "status": "ok",
        "mode": mode,
        "version": "1.0.0",
        "dll_path": os.getenv("PROFIT_DLL_PATH", ""),
        "symbols": "ibov_top20",
    }


@app.get("/quotes/{symbol}")
def quote(symbol: str):
    return _quote_for(symbol)


@app.get("/quotes")
def all_quotes():
    return [_quote_for(s) for s in IBOV_TOP20]


@app.get("/positions")
def positions():
    return []


@app.get("/trades/today")
def trades_today():
    now = datetime.utcnow().isoformat()
    seed = int(hashlib.md5(b"PETR4").hexdigest()[:8], 16)
    return {
        "trades": [
            {
                "id": "DLL-T-001",
                "symbol": "PETR4",
                "side": "buy",
                "quantity": 100,
                "price": round(8.0 + (seed % 100) / 100.0, 2),
                "fees": 0.0,
                "executed_at": now,
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PROFIT_BRIDGE_PORT", "9100"))
    uvicorn.run(app, host="0.0.0.0", port=port)
