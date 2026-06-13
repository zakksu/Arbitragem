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

logger = get_logger(__name__)


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
        wanted = {s.upper() for s in symbols if s}
        out: dict[str, ProfitQuote] = {}

        if self._should_use_bridge():
            try:
                with self._client() as client:
                    r = client.get("/quotes")
                    if r.status_code == 200:
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
            if self._should_use_bridge():
                out[sym] = self._get_quote_http(sym)
            else:
                out[sym] = self._synthetic_quote(sym)
        return out

    def _get_quote_http(self, symbol: str) -> ProfitQuote:
        sym = symbol.upper()
        if self._should_use_bridge():
            try:
                with self._client() as client:
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
        if self._should_use_bridge():
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

    def run_backtest(self, symbol: str, strategy: str = "scalp_default") -> dict[str, Any]:
        """Trigger backtest on Profit bridge (stub returns synthetic metrics)."""
        sym = symbol.upper()
        if self._should_use_bridge():
            try:
                with self._client(timeout=30.0) as client:
                    r = client.post("/backtest/run", json={"symbol": sym, "strategy": strategy})
                    if r.status_code == 200:
                        data = r.json()
                        data["symbol"] = sym
                        return data
            except Exception as exc:
                logger.warning("profit_backtest_failed", symbol=sym, error=str(exc))
        return self._synthetic_backtest(sym)

    def get_stock_option_chain(self, underlying: str) -> dict:
        sym = underlying.upper()
        if self._should_use_bridge():
            try:
                with self._client() as client:
                    r = client.get(f"/options/stock/{sym}")
                    if r.status_code == 200:
                        return r.json()
            except Exception as exc:
                logger.warning("stock_options_failed", symbol=sym, error=str(exc))
        return self._synthetic_stock_options(sym)

    @staticmethod
    def _synthetic_backtest(symbol: str) -> dict[str, Any]:
        seed = _symbol_seed(symbol)
        pf = round(1.1 + (seed % 90) / 100.0, 2)
        dd = round(2.0 + (seed % 60) / 10.0, 2)
        return {
            "symbol": symbol,
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


def get_profit_client() -> ProfitBridgeClient:
    return _profit_client_singleton()


@lru_cache(maxsize=1)
def _profit_client_singleton() -> ProfitBridgeClient:
    return ProfitBridgeClient()
