"""ProfitDLL HTTP bridge — run on Windows next to ProfitChart / ProfitPro.

Provides per-symbol quotes for IBOV Top 20 development and testing.
Replace with real ProfitDLL ctypes when Nelogica credentials are available.

Usage:
    python scripts/profit_bridge_stub.py
Set in .env:
    PROFIT_BRIDGE_ENABLED=true
    PROFIT_BRIDGE_URL=http://localhost:9100
"""

from __future__ import annotations

import hashlib
from datetime import datetime

from fastapi import FastAPI

# IBOV top 20 — inline for standalone bridge (no PYTHONPATH required)
IBOV_TOP20 = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3", "ABEV3", "B3SA3", "WEGE3",
    "RENT3", "MGLU3", "VIVT3", "BBSE3", "SUZB3", "PRIO3", "RADL3", "JBSS3",
    "BPAC11", "EQTL3", "GGBR4", "BOVA11",
]

app = FastAPI(title="Profit Bridge Stub", version="1.0.0")


def _symbol_seed(symbol: str) -> int:
    return int(hashlib.md5(symbol.upper().encode()).hexdigest()[:8], 16)


def _quote_for(symbol: str) -> dict:
    sym = symbol.upper()
    seed = _symbol_seed(sym)
    base = 8.0 + (seed % 5000) / 100.0
    spread = 0.01 + (seed % 7) / 1000.0
    volume = 800_000 + (seed % 9_000_000)
    last = round(base + (seed % 100) / 1000.0, 2)
    bid = round(last - spread / 2, 2)
    ask = round(last + spread / 2, 2)
    return {
        "symbol": sym,
        "bid": bid,
        "ask": ask,
        "last": last,
        "volume": volume,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health")
def health():
    return {"status": "ok", "mode": "stub", "version": "1.0.0", "symbols": "ibov_top20"}


@app.get("/quotes/{symbol}")
def quote(symbol: str):
    return _quote_for(symbol)


@app.get("/quotes")
def all_quotes():
    core14 = [
        "PETR4", "VALE3", "PRIO3", "ITUB4", "BBAS3", "BBDC4", "BBSE3", "B3SA3",
        "ABEV3", "GGBR4", "CSNA3", "USIM5", "SUZB3", "WEGE3", "BOVA11",
    ]
    return [_quote_for(s) for s in core14]


@app.get("/options/bova")
def bova_options_chain():
    """Near-month BOVA index options (stub)."""
    und = _quote_for("BOVA11")
    last = und["last"]
    base = int(round(last))
    calls, puts = [], []
    for i in range(-2, 3):
        strike = base + i
        seed = _symbol_seed(f"BOVAX{strike}")
        calls.append(
            {
                "symbol": f"BOVAX{strike}",
                "type": "call",
                "strike": float(strike),
                "last": round(0.5 + (seed % 50) / 100.0, 2),
                "volume": 1000 + seed % 50000,
                "open_interest": 5000 + seed % 200000,
            }
        )
        puts.append(
            {
                "symbol": f"BOVAY{strike}",
                "type": "put",
                "strike": float(strike),
                "last": round(0.4 + (seed % 40) / 100.0, 2),
                "volume": 800 + seed % 40000,
                "open_interest": 4000 + seed % 180000,
            }
        )
    return {
        "underlying": "BOVA11",
        "underlying_last": last,
        "expiry": "near-month",
        "calls": calls,
        "puts": puts,
    }


@app.get("/positions")
def positions():
    return []


@app.get("/trades/today")
def trades_today():
    """Today's executed trades from Profit automation (stub)."""
    now = datetime.utcnow().isoformat()
    trades = [
        {
            "id": "PROFIT-T-001",
            "symbol": "PETR4",
            "side": "buy",
            "quantity": 100,
            "price": 36.42,
            "fees": 0.0,
            "pnl": None,
            "executed_at": now,
        },
        {
            "id": "PROFIT-T-002",
            "symbol": "PETR4",
            "side": "sell",
            "quantity": 100,
            "price": 36.58,
            "fees": 0.0,
            "pnl": 16.0,
            "executed_at": now,
        },
    ]
    return {"trades": trades}


@app.post("/backtest/run")
def run_backtest(payload: dict):
    sym = str(payload.get("symbol", "PETR4")).upper()
    seed = _symbol_seed(sym)
    pf = round(1.15 + (seed % 85) / 100.0, 2)
    dd = round(2.5 + (seed % 55) / 10.0, 2)
    return {
        "symbol": sym,
        "strategy": payload.get("strategy", "scalp_default"),
        "profit_factor": pf,
        "max_drawdown_pct": dd,
        "trades": 100 + seed % 120,
        "win_rate_pct": 48 + seed % 15,
        "source": "stub",
    }


@app.get("/options/stock/{underlying}")
def stock_options(underlying: str):
    sym = underlying.upper()
    und = _quote_for(sym)
    last = und["last"]
    base = int(round(last))
    calls, puts = [], []
    for i in range(-1, 2):
        strike = base + i
        seed = _symbol_seed(f"{sym}O{strike}")
        prefix = sym[:4]
        calls.append(
            {
                "symbol": f"{prefix}X{strike}",
                "type": "call",
                "strike": float(strike),
                "last": round(0.35 + (seed % 40) / 100.0, 2),
                "volume": 500 + seed % 20000,
            }
        )
        puts.append(
            {
                "symbol": f"{prefix}Y{strike}",
                "type": "put",
                "strike": float(strike),
                "last": round(0.3 + (seed % 35) / 100.0, 2),
                "volume": 400 + seed % 18000,
            }
        )
    return {"underlying": sym, "underlying_last": last, "calls": calls, "puts": puts}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9100)
