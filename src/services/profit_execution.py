"""ProfitChart order execution — bridge tickets (no Clear API)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.config import get_settings
from src.integrations.profit_bridge import get_profit_client
from src.logging_config import get_logger
from src.services.capital_manager import apply_sizing_to_legs
from src.services.idea_levels import enrich_idea_levels
from src.services.paper_execution import paper_fill_price
from src.services.profit_accounts import resolve_profit_account

logger = get_logger(__name__)


def submit_order(
    *,
    symbol: str,
    side: str,
    quantity: int,
    order_type: str = "market",
    price: float | None = None,
    idea_id: int | None = None,
    stop_price: float | None = None,
    target_price: float | None = None,
) -> dict[str, Any]:
    """POST order to Profit bridge — sim auto-fill or live ticket outbox."""
    client = get_profit_client()
    account = resolve_profit_account()
    payload = {
        "symbol": symbol.upper(),
        "side": side.lower(),
        "quantity": int(quantity),
        "order_type": order_type,
        "price": price,
        "idea_id": idea_id,
        "stop_price": stop_price,
        "target_price": target_price,
        "account_profile": account["profile"],
        "account_id": account["account_id"],
        "is_paper": account["is_paper"],
    }
    result = client.place_order(payload)
    logger.info(
        "profit_order_submitted",
        symbol=symbol,
        side=side,
        qty=quantity,
        status=result.get("status"),
        ticket_id=result.get("ticket_id"),
    )
    return result


def execute_idea_via_profit(idea: dict[str, Any]) -> list[dict[str, Any]]:
    """Size legs and submit each to Profit bridge."""
    enriched = enrich_idea_levels(idea)
    sized_legs = apply_sizing_to_legs(enriched)
    fills: list[dict[str, Any]] = []
    entry = enriched.get("entry_price")
    stop = enriched.get("stop_price")
    target = enriched.get("target_price")

    for leg in sized_legs:
        side = leg.get("side", "buy")
        if side == "flat":
            continue
        sym = str(leg.get("symbol", idea.get("symbol", "")))
        qty = int(leg.get("quantity", 100))
        quote = get_profit_client().get_quote(sym)
        limit = paper_fill_price(quote, side, entry) if quote else entry
        fill = submit_order(
            symbol=sym,
            side=side,
            quantity=qty,
            order_type="market",
            price=limit,
            idea_id=idea.get("id"),
            stop_price=stop,
            target_price=target,
        )
        fills.append(fill)
    return fills


def pending_tickets() -> list[dict[str, Any]]:
    return get_profit_client().get_pending_orders()
