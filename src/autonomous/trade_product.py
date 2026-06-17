"""Trade product helpers for autonomous promotion."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.services.trade_product import build_trade_product


class AutonomousTradeProduct:
    def __init__(self, session: Session) -> None:
        self.session = session

    def for_symbol(self, symbol: str) -> dict[str, Any]:
        idea = {"symbol": symbol.strip().upper(), "structure_type": "scalp_long", "side": "long"}
        return build_trade_product(idea, session=self.session)
