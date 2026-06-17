"""Live desk — positions, open orders, today's trades."""

from __future__ import annotations

from datetime import datetime, time

from sqlalchemy.orm import Session

from src.integrations.profit_bridge import get_profit_client
from src.models import Trade, TradeIdea


def build_trading_desk(session: Session) -> dict:
    from src.services.profit_execution import pending_tickets

    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    profit = get_profit_client()

    positions: list[dict] = []
    for p in profit.get_positions():
        positions.append(
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "avg_price": p.avg_price,
                "unrealized_pnl": p.unrealized_pnl,
                "source": "profit",
            }
        )

    open_orders: list[dict] = []
    confirmed = (
        session.query(TradeIdea)
        .filter(TradeIdea.status == "confirmed")
        .order_by(TradeIdea.confirmed_at.desc())
        .limit(8)
        .all()
    )
    for idea in confirmed:
        legs = idea.legs or [{"symbol": idea.symbol, "side": "buy", "quantity": 100}]
        for leg in legs:
            if leg.get("side") == "flat":
                continue
            open_orders.append(
                {
                    "symbol": leg.get("symbol", idea.symbol),
                    "side": leg.get("side", "buy"),
                    "quantity": leg.get("quantity", 100),
                    "status": "confirmed",
                    "idea_id": idea.id,
                }
            )

    trades = (
        session.query(Trade)
        .filter(Trade.executed_at >= today_start)
        .order_by(Trade.executed_at.desc())
        .limit(12)
        .all()
    )
    today_trades = [
        {
            "symbol": t.symbol,
            "side": t.side,
            "quantity": t.quantity,
            "price": t.price,
            "pnl": t.pnl,
            "source": t.source,
            "executed_at": t.executed_at.strftime("%H:%M") if t.executed_at else "",
        }
        for t in trades
    ]

    pending = pending_tickets()

    return {
        "positions": positions,
        "open_orders": open_orders,
        "today_trades": today_trades,
        "profit_pending": pending,
        "positions_count": len(positions),
        "orders_count": len(open_orders) + len(pending),
        "trades_count": len(today_trades),
    }
