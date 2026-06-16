"""ProfitChart / ProfitDLL bridge client.

Talks to the local HTTP bridge (scripts/profit_bridge_stub.py or real DLL wrapper).
Auto-detects bridge on localhost:9100 when PROFIT_BRIDGE_AUTO_DETECT=true.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from src.config import get_settings
from src.integrations.profit_parser import parse_profit_backtest_csv
from src.logging_config import get_logger
from src.services.metrics_utils import metrics_with_drawdown_pct

logger = get_logger(__name__)

_QUOTES_CACHE: dict[frozenset[str], tuple[float, dict[str, ProfitQuote]]] = {}
QUOTE_CACHE_TTL_SEC = 1.0


@dataclass
class ProfitQuote:
    symbol: str
    bid: float
    ask: float
    last: float
    volume: int
    timestamp: datetime


@dataclass
class ProfitPosition:
    symbol: str
    quantity: int
    avg_price: float
    unrealized_pnl: float


@dataclass
class ProfitTrade:
    external_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    fees: float
    pnl: float | None
    executed_at: datetime
    raw: dict[str, Any]


def _symbol_seed(symbol: str) -> int:
    return int(hashlib.md5(symbol.upper().encode()).hexdigest()[:8], 16)


class ProfitBridgeClient:
    """HTTP client for the Windows ProfitDLL bridge."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.profit_bridge_url.rstrip("/")
        self.enabled = self.settings.profit_bridge_enabled
        self.auto_detect = self.settings.profit_bridge_auto_detect
        self._reach_cache: tuple[float, bool] | None = None

    def _client(self, timeout: float = 5.0) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=timeout)

    def _bridge_reachable(self) -> bool:
        import time

        now = time.time()
        if self._reach_cache and now - self._reach_cache[0] < 3:
            return self._reach_cache[1]
        probe = 1.5
        try:
            with self._client(timeout=probe) as client:
                ok = client.get("/health").status_code == 200
        except Exception:
            ok = False
        self._reach_cache = (now, ok)
        return ok

    def _should_use_bridge(self) -> bool:
        if self.settings.app_env == "test":
            return self.enabled
        if self.enabled:
            return True
        return bool(self.auto_detect and self._bridge_reachable())

    def is_available(self) -> bool:
        if not self._should_use_bridge():
            return False
        return self._bridge_reachable()

    def get_quote(self, symbol: str) -> ProfitQuote | None:
        sym = symbol.upper()
        batch = self.get_quotes_batch([sym])
        return batch.get(sym)

    def get_quotes_batch(self, symbols: list[str]) -> dict[str, ProfitQuote]:
        """Fetch many quotes — one HTTP call when bridge exposes GET /quotes."""
        import time

        wanted_set = frozenset(s.upper() for s in symbols if s)
        if not wanted_set:
            return {}
        now = time.time()
        cached = _QUOTES_CACHE.get(wanted_set)
        if cached and now - cached[0] < QUOTE_CACHE_TTL_SEC:
            return dict(cached[1])

        wanted = set(wanted_set)
        out: dict[str, ProfitQuote] = {}
        batch_ok = False

        if self._should_use_bridge() and self._bridge_reachable():
            try:
                with self._client(timeout=3.0) as client:
                    r = client.get("/quotes")
                    if r.status_code == 200:
                        batch_ok = True
                        payload = r.json()
                        rows = payload if isinstance(payload, list) else payload.get("quotes", [])
                        for data in rows:
                            sym = str(data.get("symbol", "")).upper()
                            if sym not in wanted:
                                continue
                            out[sym] = ProfitQuote(
                                symbol=sym,
                                bid=float(data["bid"]),
                                ask=float(data["ask"]),
                                last=float(data["last"]),
                                volume=int(data.get("volume", 0)),
                                timestamp=datetime.fromisoformat(data["timestamp"]),
                            )
            except Exception as exc:
                logger.warning("profit_quotes_batch_failed", error=str(exc))

        for sym in wanted:
            if sym in out:
                continue
            if batch_ok and not (sym.startswith("BOVAX") or sym.startswith("BOVAY")):
                out[sym] = self._get_quote_http(sym)
            else:
                out[sym] = self._synthetic_quote(sym)
        _QUOTES_CACHE[wanted_set] = (now, dict(out))
        if len(_QUOTES_CACHE) > 8:
            oldest = min(_QUOTES_CACHE.items(), key=lambda kv: kv[1][0])[0]
            _QUOTES_CACHE.pop(oldest, None)
        return out

    def _get_quote_http(self, symbol: str) -> ProfitQuote:
        sym = symbol.upper()
        if self._should_use_bridge() and self._bridge_reachable():
            try:
                with self._client(timeout=1.5) as client:
                    r = client.get(f"/quotes/{sym}")
                    r.raise_for_status()
                    data = r.json()
                    return ProfitQuote(
                        symbol=data["symbol"],
                        bid=float(data["bid"]),
                        ask=float(data["ask"]),
                        last=float(data["last"]),
                        volume=int(data.get("volume", 0)),
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                    )
            except Exception as exc:
                logger.warning("profit_quote_failed", symbol=sym, error=str(exc))
        return self._synthetic_quote(sym)

    def get_bova_option_chain(self) -> dict:
        """Near-term BOVA11 option chain — from bridge or synthetic stub."""
        if self._should_use_bridge() and self._bridge_reachable():
            try:
                with self._client() as client:
                    r = client.get("/options/bova")
                    if r.status_code == 200:
                        return r.json()
            except Exception as exc:
                logger.warning("bova_chain_failed", error=str(exc))
        return self._synthetic_bova_chain()

    @staticmethod
    def _synthetic_bova_chain() -> dict:
        underlying = ProfitBridgeClient._synthetic_quote("BOVA11")
        last = underlying.last
        base_strike = round(last)
        calls, puts = [], []
        for i in range(-2, 3):
            strike = base_strike + i
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

    def get_positions(self) -> list[ProfitPosition]:
        if not self._should_use_bridge():
            return []
        try:
            with self._client() as client:
                r = client.get("/positions")
                r.raise_for_status()
                return [
                    ProfitPosition(
                        symbol=p["symbol"],
                        quantity=p["quantity"],
                        avg_price=p["avg_price"],
                        unrealized_pnl=p.get("unrealized_pnl", 0.0),
                    )
                    for p in r.json()
                ]
        except Exception as exc:
            logger.error("profit_positions_failed", error=str(exc))
            return []

    def get_account_summary(self) -> dict[str, Any] | None:
        """Session P&L from Profit bridge when /account is exposed."""
        if not self._should_use_bridge():
            return None
        try:
            with self._client(timeout=3.0) as client:
                r = client.get("/account")
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                data = r.json()
                return {
                    "day_pnl": float(data.get("day_pnl", 0) or 0),
                    "balance_brl": data.get("balance_brl"),
                    "source": data.get("source", "profit"),
                    "mock": data.get("mock", False),
                }
        except Exception as exc:
            logger.debug("profit_account_unavailable", error=str(exc))
            return None

    def get_trades_today(self) -> list[ProfitTrade]:
        """Optional bridge endpoint for ProfitChart fills."""
        if not self._should_use_bridge():
            return []
        try:
            with self._client() as client:
                r = client.get("/trades/today")
                if r.status_code == 404:
                    return []
                r.raise_for_status()
                payload = r.json()
                rows = payload.get("trades", payload) if isinstance(payload, dict) else payload
                out: list[ProfitTrade] = []
                for t in rows:
                    ext = str(t.get("id", t.get("external_id", "")))
                    executed = t.get("executed_at")
                    if isinstance(executed, str):
                        executed = datetime.fromisoformat(executed.replace("Z", "+00:00"))
                    out.append(
                        ProfitTrade(
                            external_id=ext,
                            symbol=t["symbol"],
                            side=t.get("side", "buy"),
                            quantity=int(t.get("quantity", 0)),
                            price=float(t.get("price", 0)),
                            fees=float(t.get("fees", 0)),
                            pnl=t.get("pnl"),
                            executed_at=executed or datetime.utcnow(),
                            raw=t,
                        )
                    )
                return out
        except Exception as exc:
            logger.debug("profit_trades_unavailable", error=str(exc))
            return []

    def export_ntsl_strategy(self, strategy_name: str, ntsl_code: str) -> Path:
        export_dir = self.settings.profit_export_path
        export_dir.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in strategy_name)
        path = export_dir / f"{safe_name}.ntsl"
        path.write_text(ntsl_code, encoding="utf-8")
        logger.info("ntsl_exported", path=str(path))
        return path

    def import_backtest_results(self, csv_path: Path) -> dict[str, Any]:
        if not csv_path.exists():
            return {"error": "file_not_found", "path": str(csv_path)}
        try:
            parsed = parse_profit_backtest_csv(csv_path).to_dict()
            parsed["source"] = "csv"
            return parsed
        except Exception as exc:
            logger.error("profit_csv_parse_failed", path=str(csv_path), error=str(exc))
            return {"error": "parse_failed", "path": str(csv_path), "message": str(exc)}

    def run_backtest(
        self,
        symbol: str,
        strategy: str = "scalp_default",
        period: str = "90d",
    ) -> dict[str, Any]:
        """Trigger backtest on Profit bridge (stub returns synthetic metrics)."""
        sym = symbol.upper()
        if self._should_use_bridge() and self._bridge_reachable():
            try:
                with self._client(timeout=30.0) as client:
                    r = client.post(
                        "/backtest/run",
                        json={"symbol": sym, "strategy": strategy, "period": period},
                    )
                    if r.status_code == 200:
                        data = r.json()
                        data["symbol"] = sym
                        return metrics_with_drawdown_pct(data)
            except Exception as exc:
                logger.warning("profit_backtest_failed", symbol=sym, error=str(exc))
        return metrics_with_drawdown_pct(
            self._synthetic_backtest(sym, strategy=strategy, period=period)
        )

    def get_session_candles(self, symbol: str, bars: int = 31) -> list[dict[str, Any]]:
        """Session OHLC for LW Charts — bridge stub or synthetic per-symbol series."""
        sym = symbol.upper()
        if self._should_use_bridge() and self._bridge_reachable():
            try:
                with self._client(timeout=3.0) as client:
                    r = client.get(f"/candles/{sym}", params={"bars": bars})
                    if r.status_code == 200:
                        payload = r.json()
                        rows = payload if isinstance(payload, list) else payload.get("candles", [])
                        if rows:
                            return rows
            except Exception as exc:
                logger.warning("session_candles_failed", symbol=sym, error=str(exc))
        return self._synthetic_session_candles(sym, bars=bars)

    @staticmethod
    def _synthetic_session_candles(symbol: str, *, bars: int = 31) -> list[dict[str, Any]]:
        import time

        seed = _symbol_seed(symbol)
        quote = ProfitBridgeClient._synthetic_quote(symbol)
        last = float(quote.last)
        now = int(time.time())
        tick = 0.01 if last < 50 else 0.05
        band = last * 0.015
        lo_band = last - band
        hi_band = last + band
        candles: list[dict[str, Any]] = []
        price = last * (1 - (seed % 20) / 2000.0)
        for i in range(bars):
            t = now - (bars - i) * 60
            wobble = ((seed + i * 13) % 100) / 10000.0
            o = round(max(lo_band, min(hi_band, price)), 2)
            c = round(max(lo_band, min(hi_band, o + wobble * last)), 2)
            h = round(min(hi_band, max(o, c) + tick * (1 + (seed + i) % 3)), 2)
            l = round(max(lo_band, min(o, c) - tick * (1 + (seed + i) % 2)), 2)
            h = max(h, o, c)
            l = min(l, o, c)
            price = c
            candles.append({"time": t, "open": o, "high": h, "low": l, "close": c})
        if candles:
            tail = candles[-1]
            tail["close"] = round(last, 2)
            tail["high"] = round(min(hi_band, max(tail["high"], tail["open"], tail["close"])), 2)
            tail["low"] = round(max(lo_band, min(tail["low"], tail["open"], tail["close"])), 2)
        return candles

    def get_stock_option_chain(self, underlying: str) -> dict:
        return self.get_option_chain(underlying)

    def get_option_chain(self, underlying: str) -> dict:
        """Unified BOVA or stock option chain."""
        sym = underlying.upper()
        if sym in ("BOVA", "BOVA11"):
            sym = "BOVA11"
        if not self.is_available():
            if sym == "BOVA11":
                return self._synthetic_bova_chain()
            return self._synthetic_stock_options(sym)
        if self._should_use_bridge() and self._bridge_reachable():
            try:
                with self._client() as client:
                    r = client.get(f"/options/chain/{sym}")
                    if r.status_code == 200:
                        return r.json()
                    if sym == "BOVA11":
                        r2 = client.get("/options/bova")
                        if r2.status_code == 200:
                            return r2.json()
                    r3 = client.get(f"/options/stock/{sym}")
                    if r3.status_code == 200:
                        return r3.json()
            except Exception as exc:
                logger.warning("option_chain_failed", symbol=sym, error=str(exc))
        if sym == "BOVA11":
            return self._synthetic_bova_chain()
        return self._synthetic_stock_options(sym)

    def get_greeks(self, symbol: str) -> dict:
        sym = symbol.upper()
        if self._should_use_bridge() and self._bridge_reachable():
            try:
                with self._client() as client:
                    r = client.get(f"/greeks/{sym}")
                    if r.status_code == 200:
                        return r.json()
            except Exception as exc:
                logger.warning("greeks_failed", symbol=sym, error=str(exc))
        seed = _symbol_seed(sym)
        return {
            "symbol": sym,
            "delta": round(0.4 + (seed % 30) / 100.0, 4),
            "gamma": 0.02,
            "theta": -0.03,
            "vega": 0.06,
            "iv": 22.0,
            "source": "synthetic",
        }

    def get_iv_rank(self, underlying: str) -> dict:
        sym = underlying.upper()
        if sym in ("BOVA", "BOVA11"):
            sym = "BOVA11"
        if not self.is_available():
            seed = _symbol_seed(sym)
            rank = round(20 + (seed % 60), 1)
            return {
                "underlying": sym,
                "iv_rank": rank,
                "iv_current": round(20 + (seed % 100) / 10.0, 2),
                "term_structure": "contango",
                "source": "synthetic",
            }
        if self._should_use_bridge() and self._bridge_reachable():
            try:
                with self._client() as client:
                    r = client.get(f"/iv-rank/{sym}")
                    if r.status_code == 200:
                        return r.json()
            except Exception as exc:
                logger.warning("iv_rank_failed", symbol=sym, error=str(exc))
        seed = _symbol_seed(sym)
        rank = round(20 + (seed % 60), 1)
        return {
            "underlying": sym,
            "iv_rank": rank,
            "iv_current": round(20 + (seed % 100) / 10.0, 2),
            "term_structure": "contango",
            "source": "synthetic",
        }

    @staticmethod
    def _synthetic_backtest(
        symbol: str,
        *,
        strategy: str = "scalp_default",
        period: str = "90d",
    ) -> dict[str, Any]:
        import uuid

        seed = _symbol_seed(f"{symbol}:{strategy}:{period}")
        pf = round(1.1 + (seed % 90) / 100.0, 2)
        dd = round(2.0 + (seed % 60) / 10.0, 2)
        return {
            "job_id": str(uuid.uuid4()),
            "status": "completed",
            "symbol": symbol,
            "strategy": strategy,
            "period": period,
            "profit_factor": pf,
            "max_drawdown_pct": dd,
            "trades": 80 + seed % 150,
            "source": "synthetic",
        }

    @staticmethod
    def _synthetic_stock_options(underlying: str) -> dict:
        q = ProfitBridgeClient._synthetic_quote(underlying)
        last = q.last
        base = int(round(last))
        calls, puts = [], []
        for i in range(-1, 2):
            strike = base + i
            seed = _symbol_seed(f"{underlying}X{strike}")
            calls.append(
                {
                    "symbol": f"{underlying[:4]}X{strike}",
                    "type": "call",
                    "strike": float(strike),
                    "last": round(0.3 + (seed % 30) / 100.0, 2),
                }
            )
            puts.append(
                {
                    "symbol": f"{underlying[:4]}Y{strike}",
                    "type": "put",
                    "strike": float(strike),
                    "last": round(0.25 + (seed % 25) / 100.0, 2),
                }
            )
        return {"underlying": underlying, "underlying_last": last, "calls": calls, "puts": puts}

    @staticmethod
    def _synthetic_quote(symbol: str) -> ProfitQuote:
        """Per-symbol fallback when bridge offline — still differentiated for dev."""
        seed = _symbol_seed(symbol)
        base = 8.0 + (seed % 5000) / 100.0
        spread = 0.01 + (seed % 7) / 1000.0
        volume = 200_000 + (seed % 8_000_000)
        last = round(base + (seed % 100) / 1000.0, 2)
        bid = round(last - spread / 2, 2)
        ask = round(last + spread / 2, 2)
        return ProfitQuote(
            symbol=symbol,
            bid=bid,
            ask=ask,
            last=last,
            volume=volume,
            timestamp=datetime.utcnow(),
        )


    def get_pending_orders(self) -> list[dict[str, Any]]:
        if not self._should_use_bridge():
            return []
        try:
            with self._client(timeout=3.0) as client:
                r = client.get("/orders/pending")
                if r.status_code == 200:
                    data = r.json()
                    return data if isinstance(data, list) else data.get("orders", [])
        except Exception as exc:
            logger.debug("profit_pending_orders_failed", error=str(exc))
        return []

    def place_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Submit market/limit order via Profit bridge (sim or ticket outbox)."""
        if self._should_use_bridge() and self._bridge_reachable():
            try:
                with self._client(timeout=8.0) as client:
                    r = client.post("/orders", json=payload)
                    if r.status_code < 400:
                        return r.json()
            except Exception as exc:
                logger.warning("profit_place_order_failed", error=str(exc))
        sym = str(payload.get("symbol", "PETR4")).upper()
        side = str(payload.get("side", "buy"))
        qty = int(payload.get("quantity", 100))
        quote = self.get_quote(sym)
        price = quote.ask if side == "buy" else quote.bid
        return {
            "ticket_id": f"local-{sym}-{int(datetime.utcnow().timestamp())}",
            "status": "filled",
            "symbol": sym,
            "side": side,
            "quantity": qty,
            "fill_price": price,
            "source": "bridge_offline_stub",
            "mock": True,
        }


def get_profit_client() -> ProfitBridgeClient:
    return _profit_client_singleton()


@lru_cache(maxsize=1)
def _profit_client_singleton() -> ProfitBridgeClient:
    return ProfitBridgeClient()
