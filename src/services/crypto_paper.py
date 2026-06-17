"""Crypto paper stub executor — Binance quotes only, no Clear/Profit (4.2 A4.24)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.integrations.profit_bridge import ProfitQuote
from src.models import JournalEntry, Trade
from src.services.crypto_quotes import get_crypto_quotes
from src.services.crypto_universe import is_crypto
from src.services.paper_execution import crypto_tick_size, paper_fill_price

_QTY_SCALE = 1000  # Trade.quantity stores milli-coins (0.001 BTC = 1)


def _require_crypto_paper(symbol: str) -> None:
    sym = symbol.strip().upper()
    if not is_crypto(sym):
        raise ValueError(f"{sym} is not a supported crypto symbol (BTC, ETH, SOL)")
    settings = get_settings()
    if not settings.crypto_paper_enabled:
        raise ValueError("Crypto paper trading is disabled (CRYPTO_PAPER_ENABLED=false)")
    if not settings.paper_trading_mode:
        raise ValueError("Crypto live execution is not supported — enable PAPER_TRADING_MODE")


def _scaled_quantity(qty_crypto: float) -> int:
    return max(1, int(round(qty_crypto * _QTY_SCALE)))


def preview_crypto_fill(
    *,
    symbol: str,
    side: str,
    quantity: float,
) -> dict[str, Any]:
    """Fill preview for crypto paper stub — same slippage model as equities."""
    _require_crypto_paper(symbol)
    if quantity <= 0:
        raise ValueError("quantity must be positive")

    sym = symbol.strip().upper()
    quote = get_crypto_quotes([sym]).get(sym)
    if not quote:
        raise ValueError(f"No quote for {sym}")

    side_l = side.lower()
    if side_l not in ("buy", "sell", "long", "short"):
        raise ValueError("side must be buy/sell or long/short")
    if side_l in ("long", "buy"):
        side_l = "buy"
    else:
        side_l = "sell"

    tick = crypto_tick_size(sym, quote.last)
    ideal = round(quote.last, 4)
    expected = paper_fill_price(quote, side_l, quote.last)
    slip_ticks = round(abs(expected - ideal) / tick, 2) if tick else 0.0
    notional = round(expected * quantity, 2)

    return {
        "symbol": sym,
        "side": side_l,
        "quantity_crypto": quantity,
        "ideal_price": ideal,
        "expected_fill": expected,
        "slippage_ticks": slip_ticks,
        "notional_usd": notional,
        "quote_source": "binance",
        "paper_only": True,
        "auto_trade": False,
        "quote_bid": quote.bid,
        "quote_ask": quote.ask,
    }


def execute_crypto_paper(
    session: Session,
    *,
    symbol: str,
    side: str,
    quantity: float,
    note: str | None = None,
) -> dict[str, Any]:
    """Record a paper crypto fill in journal + trades — never routes to Clear."""
    preview = preview_crypto_fill(symbol=symbol, side=side, quantity=quantity)
    sym = preview["symbol"]
    side_l = preview["side"]
    fill_price = float(preview["expected_fill"])
    qty_scaled = _scaled_quantity(quantity)
    ext_id = f"crypto-paper-{sym}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"

    trade = Trade(
        external_id=ext_id,
        source="paper_crypto",
        symbol=sym,
        side=side_l,
        quantity=qty_scaled,
        price=fill_price,
        fees=0.0,
        executed_at=datetime.now(UTC),
        raw_payload={
            "qty_crypto": quantity,
            "qty_scale": _QTY_SCALE,
            "slippage_model": "spread_plus_1_tick",
            "quote_source": preview.get("quote_source"),
            "paper_only": True,
            **preview,
        },
    )
    session.add(trade)
    session.flush()
    session.add(
        JournalEntry(
            title=f"Paper crypto {side_l.upper()} {sym}",
            content=note or f"Stub fill {quantity} {sym} @ {fill_price} (Binance quote, paper only).",
            tags=["paper", "crypto", sym.lower()],
            ai_generated=False,
        )
    )
    session.commit()
    return {
        "trade_id": trade.id,
        "external_id": ext_id,
        "source": "paper_crypto",
        "read_only": False,
        "paper_only": True,
        **preview,
    }


def quote_for_symbol(symbol: str) -> ProfitQuote | None:
    """Unified quote lookup — crypto via Binance stub, else Profit bridge."""
    sym = symbol.strip().upper()
    if is_crypto(sym):
        return get_crypto_quotes([sym]).get(sym)
    from src.integrations.profit_bridge import get_profit_client

    return get_profit_client().get_quote(sym)


def idea_uses_crypto(idea: dict[str, Any] | Any) -> bool:
    if isinstance(idea, dict):
        sym = str(idea.get("symbol", "")).upper()
        legs = idea.get("legs") or []
    else:
        sym = str(getattr(idea, "symbol", "") or "").upper()
        legs = getattr(idea, "legs", None) or []
    if is_crypto(sym):
        return True
    return any(
        is_crypto(str(leg.get("symbol", "") if isinstance(leg, dict) else getattr(leg, "symbol", "")))
        for leg in legs
    )
