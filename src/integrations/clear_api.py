"""Clear Corretora Smart Trader API client (placeholder with mock mode)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any

import httpx

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ClearOrder:
    symbol: str
    side: str
    quantity: int
    order_type: str = "market"
    price: float | None = None


@dataclass
class ClearTrade:
    external_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    fees: float
    executed_at: datetime
    raw: dict[str, Any]


class ClearAPIClient:
    """Smart Trader API wrapper. Uses mock data when credentials are missing."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.clear_api_base_url.rstrip("/")
        self.mock_mode = not bool(self.settings.clear_api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.clear_api_key}",
            "X-API-Secret": self.settings.clear_api_secret,
            "Content-Type": "application/json",
        }

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, headers=self._headers(), timeout=15.0)

    def is_configured(self) -> bool:
        return not self.mock_mode

    def get_account_summary(self) -> dict[str, Any]:
        if self.mock_mode:
            return {
                "account_id": "MOCK-001",
                "balance_brl": 50000.0,
                "available_margin": 45000.0,
                "day_pnl": 125.50,
                "mock": True,
            }
        try:
            with self._client() as client:
                r = client.get(f"/accounts/{self.settings.clear_account_id}/summary")
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            logger.error("clear_account_failed", error=str(exc))
            raise

    def get_positions(self) -> list[dict[str, Any]]:
        if self.mock_mode:
            return [
                {"symbol": "PETR4", "quantity": 200, "avg_price": 38.42, "unrealized_pnl": 48.0},
                {"symbol": "BOVAX125", "quantity": 100, "avg_price": 0.45, "unrealized_pnl": 32.0},
            ]
        try:
            with self._client() as client:
                r = client.get(f"/accounts/{self.settings.clear_account_id}/positions")
                r.raise_for_status()
                return r.json().get("positions", [])
        except Exception as exc:
            logger.error("clear_positions_failed", error=str(exc))
            return []

    def get_trades_today(self) -> list[ClearTrade]:
        if self.mock_mode:
            now = datetime.utcnow()
            return [
                ClearTrade(
                    external_id="MOCK-T-001",
                    symbol="PETR4",
                    side="buy",
                    quantity=200,
                    price=38.40,
                    fees=2.50,
                    executed_at=now,
                    raw={"mock": True},
                ),
                ClearTrade(
                    external_id="MOCK-T-002",
                    symbol="PETR4",
                    side="sell",
                    quantity=200,
                    price=38.65,
                    fees=2.50,
                    executed_at=now,
                    raw={"mock": True},
                ),
                ClearTrade(
                    external_id="MOCK-T-003",
                    symbol="BOVAX125",
                    side="buy",
                    quantity=100,
                    price=0.44,
                    fees=0.0,
                    executed_at=now,
                    raw={"mock": True},
                ),
            ]
        try:
            with self._client() as client:
                r = client.get(f"/accounts/{self.settings.clear_account_id}/trades/today")
                r.raise_for_status()
                return [
                    ClearTrade(
                        external_id=t["id"],
                        symbol=t["symbol"],
                        side=t["side"],
                        quantity=t["quantity"],
                        price=t["price"],
                        fees=t.get("fees", 0.0),
                        executed_at=datetime.fromisoformat(t["executed_at"]),
                        raw=t,
                    )
                    for t in r.json().get("trades", [])
                ]
        except Exception as exc:
            logger.error("clear_trades_failed", error=str(exc))
            return []

    def place_order(self, order: ClearOrder) -> dict[str, Any]:
        if self.mock_mode:
            logger.info("clear_mock_order", symbol=order.symbol, side=order.side, qty=order.quantity)
            return {"status": "accepted", "order_id": "MOCK-ORD-001", "mock": True}
        payload = {
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "type": order.order_type,
            "price": order.price,
        }
        try:
            with self._client() as client:
                r = client.post(f"/accounts/{self.settings.clear_account_id}/orders", json=payload)
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            logger.error("clear_order_failed", error=str(exc))
            raise


def get_clear_client() -> ClearAPIClient:
    return _clear_client_singleton()


@lru_cache(maxsize=1)
def _clear_client_singleton() -> ClearAPIClient:
    return ClearAPIClient()
