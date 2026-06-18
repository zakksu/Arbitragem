"""R$1k live rule — 1 WIN contract OR 1 stock lot, never both full size (13.0)."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.models import Trade, TradeIdea


def _is_win(symbol: str) -> bool:
    return symbol.upper().startswith("WIN")


def _is_stock_cash(symbol: str) -> bool:
    sym = symbol.upper()
    if _is_win(sym) or sym.startswith("WDO"):
        return False
    return len(sym) <= 6 and sym[-1].isdigit()


def open_live_exposure(session: Session) -> dict[str, Any]:
    """Summarize open exposure for capital gate."""
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    ideas = (
        session.query(TradeIdea)
        .filter(TradeIdea.status.in_(("confirmed", "executed")))
        .filter(TradeIdea.executed_at >= today_start)
        .all()
    )
    win_open = 0
    stock_lots = 0
    for idea in ideas:
        sym = (idea.symbol or "").upper()
        if _is_win(sym):
            win_open += 1
        elif _is_stock_cash(sym):
            stock_lots += 1
    trades = session.query(Trade).filter(Trade.executed_at >= today_start).all()
    for t in trades:
        sym = (t.symbol or "").upper()
        if _is_win(sym):
            win_open += 1
        elif _is_stock_cash(sym):
            stock_lots += 1
    return {"win_contracts": win_open, "stock_lots": stock_lots}


def live_capital_block(session: Session, symbol: str, quantity: int) -> str | None:
    """Return error message if new order violates R$1k stacking rule."""
    settings = get_settings()
    if settings.paper_trading_mode:
        return None
    capital = float(settings.live_capital_brl or 1000.0)
    if capital > 1500:
        return None

    sym = symbol.upper()
    exp = open_live_exposure(session)
    lot = int(settings.motor_fixed_lot_shares or 100)

    if _is_win(sym):
        if exp["stock_lots"] > 0:
            return "R$1k rule: close stock lot before adding WIN"
        if exp["win_contracts"] >= 1 and quantity >= 1:
            return "R$1k rule: max 1 WIN contract"
        return None

    if _is_stock_cash(sym):
        if exp["win_contracts"] > 0:
            return "R$1k rule: close WIN before full stock lot"
        if quantity >= lot and exp["stock_lots"] >= 1:
            return "R$1k rule: max 1 stock lot (100 sh)"
        return None

    return None
