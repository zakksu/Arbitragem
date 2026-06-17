"""ProfitDLL HTTP bridge — run on Windows next to ProfitChart / ProfitPro.

Provides per-symbol quotes for Core14 + BOVA development and testing.
Replace with real ProfitDLL ctypes when Nelogica credentials are available.

Usage:
    python scripts/profit_bridge_stub.py
Set in .env:
    PROFIT_BRIDGE_ENABLED=true
    PROFIT_BRIDGE_URL=http://localhost:9100
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI

ROOT = Path(__file__).resolve().parents[1]
OUTBOX = ROOT / "data" / "profit_outbox"
OUTBOX.mkdir(parents=True, exist_ok=True)
(OUTBOX / "pending").mkdir(parents=True, exist_ok=True)

_STUB_POSITIONS: dict[str, dict] = {}
_PENDING_ORDERS: list[dict] = []

CORE14 = [
    "PETR4", "VALE3", "PRIO3", "ITUB4", "BBAS3", "BBDC4", "BBSE3", "B3SA3",
    "ABEV3", "GGBR4", "CSNA3", "USIM5", "SUZB3", "WEGE3",
]
BOVA_UNDERLYING = "BOVA11"

app = FastAPI(title="Profit Bridge Stub", version="3.0.0-alpha")


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


def _is_bova_underlying(sym: str) -> bool:
    return sym in (BOVA_UNDERLYING, "BOVA")


def _option_prefix(underlying: str) -> tuple[str, str]:
    """Return (call_prefix, put_prefix) for option symbols."""
    if _is_bova_underlying(underlying):
        return "BOVAX", "BOVAY"
    return underlying[:4] + "X", underlying[:4] + "Y"


def _synthetic_greeks(symbol: str, opt_type: str, strike: float, last: float) -> dict:
    seed = _symbol_seed(symbol)
    delta = round(0.35 + (seed % 40) / 100.0, 4)
    if opt_type == "put":
        delta = -abs(delta)
    gamma = round(0.01 + (seed % 8) / 1000.0, 4)
    theta = round(-0.02 - (seed % 15) / 1000.0, 4)
    vega = round(0.05 + (seed % 20) / 1000.0, 4)
    iv = round(18.0 + (seed % 250) / 10.0, 2)
    return {
        "symbol": symbol,
        "delta": delta,
        "gamma": gamma,
        "theta": theta,
        "vega": vega,
        "iv": iv,
        "strike": strike,
        "underlying_last": last,
        "source": "stub",
    }


def _build_chain(underlying: str, strike_range: int = 3) -> dict:
    sym = underlying.upper()
    if _is_bova_underlying(sym):
        und_sym = BOVA_UNDERLYING
    else:
        und_sym = sym
    und = _quote_for(und_sym)
    last = und["last"]
    base = int(round(last))
    call_pfx, put_pfx = _option_prefix(und_sym)
    calls, puts = [], []
    for i in range(-strike_range, strike_range + 1):
        strike = base + i
        c_seed = _symbol_seed(f"{call_pfx}{strike}")
        p_seed = _symbol_seed(f"{put_pfx}{strike}")
        c_sym = f"{call_pfx}{strike}"
        p_sym = f"{put_pfx}{strike}"
        c_last = round(0.45 + (c_seed % 55) / 100.0, 2)
        p_last = round(0.38 + (p_seed % 48) / 100.0, 2)
        c_spread = 0.02 + (c_seed % 5) / 100.0
        p_spread = 0.02 + (p_seed % 5) / 100.0
        calls.append(
            {
                "symbol": c_sym,
                "type": "call",
                "strike": float(strike),
                "bid": round(c_last - c_spread / 2, 2),
                "ask": round(c_last + c_spread / 2, 2),
                "last": c_last,
                "volume": 1200 + c_seed % 80000,
                "open_interest": 8000 + c_seed % 350000,
                "iv": round(20.0 + (c_seed % 180) / 10.0, 2),
            }
        )
        puts.append(
            {
                "symbol": p_sym,
                "type": "put",
                "strike": float(strike),
                "bid": round(p_last - p_spread / 2, 2),
                "ask": round(p_last + p_spread / 2, 2),
                "last": p_last,
                "volume": 900 + p_seed % 70000,
                "open_interest": 7000 + p_seed % 320000,
                "iv": round(19.0 + (p_seed % 200) / 10.0, 2),
            }
        )
    return {
        "underlying": und_sym,
        "underlying_last": last,
        "expiry": "near-month",
        "calls": calls,
        "puts": puts,
        "source": "stub",
    }


def _max_pain_from_chain(chain: dict) -> dict:
    calls = chain.get("calls") or []
    puts = chain.get("puts") or []
    strikes = {float(l["strike"]) for l in calls + puts if l.get("strike") is not None}
    if not strikes:
        return {}
    underlying_last = float(chain.get("underlying_last") or 0)
    pain_by_strike: dict[float, float] = {}
    for test_strike in strikes:
        total = 0.0
        for call in calls:
            strike = float(call.get("strike", 0))
            oi = float(call.get("open_interest") or call.get("volume") or 0)
            if test_strike > strike:
                total += (test_strike - strike) * oi
        for put in puts:
            strike = float(put.get("strike", 0))
            oi = float(put.get("open_interest") or put.get("volume") or 0)
            if test_strike < strike:
                total += (strike - test_strike) * oi
        pain_by_strike[test_strike] = total
    max_pain_strike = min(pain_by_strike, key=pain_by_strike.get)
    distance_pct = None
    if underlying_last > 0:
        distance_pct = round((underlying_last - max_pain_strike) / underlying_last * 100, 3)
    return {
        "underlying": chain.get("underlying"),
        "max_pain_strike": max_pain_strike,
        "underlying_last": underlying_last,
        "distance_pct": distance_pct,
        "source": "stub",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": "stub",
        "version": "3.0.0-alpha",
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
    if _is_bova_underlying(sym):
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
    seed = _symbol_seed(sym)
    if "X" in sym[4:] or sym.startswith("BOVAX"):
        opt_type = "call"
        strike = float("".join(c for c in sym if c.isdigit()) or seed % 100)
    elif "Y" in sym[4:] or sym.startswith("BOVAY"):
        opt_type = "put"
        strike = float("".join(c for c in sym if c.isdigit()) or seed % 100)
    else:
        opt_type = "stock"
        strike = 0.0
    und_last = _quote_for(sym[:4] + "4" if len(sym) > 6 else BOVA_UNDERLYING)["last"]
    if opt_type == "stock":
        return {
            "symbol": sym,
            "delta": 1.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "iv": 0.0,
            "source": "stub",
        }
    return _synthetic_greeks(sym, opt_type, strike, und_last)


@app.get("/iv-rank/{underlying}")
def iv_rank(underlying: str):
    sym = underlying.upper()
    if _is_bova_underlying(sym):
        sym = BOVA_UNDERLYING
    seed = _symbol_seed(sym)
    rank = round(15 + (seed % 75), 1)
    iv_current = round(18.0 + (seed % 200) / 10.0, 2)
    iv_52w_high = round(iv_current + 4 + (seed % 80) / 10.0, 2)
    iv_52w_low = round(max(8.0, iv_current - 6 - (seed % 50) / 10.0), 2)
    term = "contango" if seed % 2 else "backwardation"
    return {
        "underlying": sym,
        "iv_rank": rank,
        "iv_current": iv_current,
        "iv_52w_high": iv_52w_high,
        "iv_52w_low": iv_52w_low,
        "term_structure": term,
        "source": "stub",
    }


@app.get("/positions")
def positions():
    out = []
    for sym, p in _STUB_POSITIONS.items():
        out.append(
            {
                "symbol": sym,
                "quantity": p["quantity"],
                "avg_price": p["avg_price"],
                "unrealized_pnl": p.get("unrealized_pnl", 0.0),
            }
        )
    return out


@app.get("/orders/pending")
def pending_orders():
    return list(_PENDING_ORDERS)


@app.post("/orders")
def place_order(payload: dict):
    """Motor ticket — sim auto-fills; live writes outbox for ProfitChart / NTSL."""
    ticket_id = str(uuid.uuid4())[:8]
    sym = str(payload.get("symbol", "")).upper()
    side = str(payload.get("side", "buy")).lower()
    qty = int(payload.get("quantity", 100))
    is_paper = bool(payload.get("is_paper", True))
    q = _quote_for(sym)
    fill_price = round(q["ask"] if side == "buy" else q["bid"], 4)

    ticket = {
        "ticket_id": ticket_id,
        "symbol": sym,
        "side": side,
        "quantity": qty,
        "order_type": payload.get("order_type", "market"),
        "price": payload.get("price") or fill_price,
        "stop_price": payload.get("stop_price"),
        "target_price": payload.get("target_price"),
        "idea_id": payload.get("idea_id"),
        "account_profile": payload.get("account_profile", "sim"),
        "account_id": payload.get("account_id"),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "chart_trading_hint": (
            f"{'C' if side == 'buy' else 'V'} Mercado · {qty} · {sym}"
        ),
    }
    (OUTBOX / "next_order.json").write_text(json.dumps(ticket, indent=2), encoding="utf-8")
    (OUTBOX / "pending" / f"{ticket_id}.json").write_text(
        json.dumps(ticket, indent=2), encoding="utf-8"
    )

    if is_paper:
        signed = qty if side == "buy" else -qty
        pos = _STUB_POSITIONS.get(sym, {"quantity": 0, "avg_price": fill_price, "unrealized_pnl": 0.0})
        old_q = pos["quantity"]
        new_q = old_q + signed
        if new_q == 0:
            _STUB_POSITIONS.pop(sym, None)
        else:
            pos["quantity"] = new_q
            pos["avg_price"] = fill_price
            pos["unrealized_pnl"] = round((q["last"] - fill_price) * new_q, 2)
            _STUB_POSITIONS[sym] = pos
        return {
            **ticket,
            "status": "filled",
            "fill_price": fill_price,
            "source": "profit_sim",
        }

    _PENDING_ORDERS.append({**ticket, "status": "pending"})
    return {**ticket, "status": "pending", "source": "profit_outbox"}


@app.get("/account")
def account():
    trades = trades_today()["trades"]
    day_pnl = round(sum(float(t.get("pnl") or 0) for t in trades), 2)
    return {
        "day_pnl": day_pnl,
        "balance_brl": 50_000.0,
        "source": "profit_stub",
        "mock": True,
    }


@app.get("/trades/today")
def trades_today():
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


_REPLAY_JOBS: dict[str, dict] = {}


def _synthetic_replay_fills(symbol: str, *, bars: int = 40) -> list[dict]:
    """Tick-style fills from stub candles — bridge replay training."""
    sym = symbol.upper()
    seed = _symbol_seed(sym)
    last = _quote_for(sym)["last"]
    fills: list[dict] = []
    price = last * 0.995
    for i in range(0, bars, 8):
        entry = round(price + (seed % 10) / 100.0, 2)
        exit_p = round(entry + (1 if i % 16 == 0 else -1) * 0.08, 2)
        pnl = round((exit_p - entry) * 100, 2)
        fills.append(
            {
                "side": "buy",
                "price": entry,
                "quantity": 100,
                "tick_index": i,
                "event": "entry_long",
            }
        )
        fills.append(
            {
                "side": "sell",
                "price": exit_p,
                "quantity": 100,
                "pnl": pnl,
                "tick_index": i + 4,
                "event": "exit_long",
            }
        )
        price = exit_p
    return fills


@app.post("/replay/run")
def replay_run(payload: dict):
    sym = str(payload.get("symbol", "PETR4")).upper()
    job_id = str(uuid.uuid4())[:8]
    speed = float(payload.get("speed") or 10)
    fills = _synthetic_replay_fills(sym)
    wins = sum(1 for f in fills if f.get("pnl") and f["pnl"] > 0)
    closed = sum(1 for f in fills if f.get("event", "").startswith("exit"))
    total_pnl = sum(float(f.get("pnl") or 0) for f in fills)
    metrics = {
        "symbol": sym,
        "strategy": payload.get("strategy", "scalp_default"),
        "fills": len(fills),
        "round_trips": closed,
        "wins": wins,
        "total_pnl": round(total_pnl, 2),
        "win_rate_pct": round(wins / closed * 100, 1) if closed else 0,
        "engine": "profit_bridge_stub",
        "speed": speed,
    }
    job = {
        "job_id": job_id,
        "status": "completed",
        "symbol": sym,
        "progress_pct": 100,
        "fills": fills,
        "metrics": metrics,
        "message": "Stub tick replay complete",
    }
    _REPLAY_JOBS[job_id] = job
    return job


@app.get("/replay/{job_id}")
def replay_status(job_id: str):
    job = _REPLAY_JOBS.get(job_id)
    if not job:
        return {"status": "not_found", "job_id": job_id}
    return job


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9100)
