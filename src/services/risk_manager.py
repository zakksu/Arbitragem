"""Risk management — enforces daily loss and position limits."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.logging_config import get_logger
from src.models import Strategy, Trade

logger = get_logger(__name__)


@dataclass
class RiskCheckResult:
    allowed: bool
    reason: str = ""


class RiskManager:
    def __init__(self, session: Session) -> None:
        self.session = session

    def check_can_start(self, strategy: Strategy) -> RiskCheckResult:
        """Pre-flight check before activating a strategy."""
        day_pnl = self._strategy_day_pnl(strategy.id)
        if day_pnl <= -abs(strategy.daily_loss_limit_brl):
            return RiskCheckResult(
                False,
                f"Daily loss limit already hit: R$ {day_pnl:.2f} (limit R$ {strategy.daily_loss_limit_brl})",
            )
        if strategy.daily_loss_limit_brl <= 0:
            return RiskCheckResult(False, "Daily loss limit must be positive")
        if strategy.max_contracts < 1:
            return RiskCheckResult(False, "Max contracts must be at least 1")
        return RiskCheckResult(True, "OK")

    def check_strategy_order(
        self,
        strategy: Strategy,
        symbol: str,
        quantity: int,
        open_positions_count: int,
    ) -> RiskCheckResult:
        if strategy.status != "active":
            return RiskCheckResult(False, f"Strategy '{strategy.name}' is not active")

        if quantity > strategy.max_contracts:
            return RiskCheckResult(
                False,
                f"Quantity {quantity} exceeds max contracts {strategy.max_contracts}",
            )

        if open_positions_count >= strategy.max_open_positions:
            return RiskCheckResult(
                False,
                f"Max open positions ({strategy.max_open_positions}) reached",
            )

        day_pnl = self._strategy_day_pnl(strategy.id)
        if day_pnl <= -abs(strategy.daily_loss_limit_brl):
            return RiskCheckResult(
                False,
                f"Daily loss limit hit: R$ {day_pnl:.2f} (limit R$ {strategy.daily_loss_limit_brl})",
            )

        return RiskCheckResult(True, "OK")

    def _strategy_day_pnl(self, strategy_id: int) -> float:
        from datetime import datetime, time

        today_start = datetime.combine(datetime.utcnow().date(), time.min)
        result = (
            self.session.query(func.coalesce(func.sum(Trade.pnl), 0.0))
            .filter(Trade.strategy_id == strategy_id, Trade.executed_at >= today_start)
            .scalar()
        )
        return float(result or 0.0)
