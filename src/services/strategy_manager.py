"""Strategy lifecycle management."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.integrations.profit_bridge import get_profit_client
from src.logging_config import get_logger
from src.models import Strategy, StrategyStatus
from src.services.risk_manager import RiskManager

logger = get_logger(__name__)

SAMPLE_NTSL = """
// Sample BOVA scalping template — replace with your Edge
Input
  StopTicks(5);
  TargetTicks(8);
  MaxContratos(2);

Var
  entrada : Boolean;

Begin
  entrada := (Close > Media(9, Close)) and (Volume > Media(20, Volume));
  if entrada and (BuyPosition = 0) then
    BuyAtMarket(MaxContratos);
  if (BuyPosition > 0) and (Close <= BuyPrice - StopTicks * MinPriceIncrement) then
    SellToCoverAtMarket(BuyPosition);
  if (BuyPosition > 0) and (Close >= BuyPrice + TargetTicks * MinPriceIncrement) then
    SellToCoverAtMarket(BuyPosition);
End;
""".strip()


class StrategyService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.profit = get_profit_client()

    def list_strategies(self) -> list[Strategy]:
        return self.session.query(Strategy).order_by(Strategy.name).all()

    def get_or_create_sample(self) -> Strategy:
        existing = self.session.query(Strategy).filter(Strategy.name == "BOVA Scalp MVP").first()
        if existing:
            return existing
        strategy = Strategy(
            name="BOVA Scalp MVP",
            description="Starter NTSL template for dashboard testing",
            ntsl_code=SAMPLE_NTSL,
            status=StrategyStatus.DRAFT.value,
            parameters={"stop_ticks": 5, "target_ticks": 8, "max_contracts": 2},
        )
        self.session.add(strategy)
        self.session.commit()
        return strategy

    def start_strategy(self, strategy_id: int) -> Strategy:
        strategy = self.session.get(Strategy, strategy_id)
        if not strategy:
            raise ValueError("Strategy not found")

        risk = RiskManager(self.session).check_can_start(strategy)
        if not risk.allowed:
            raise ValueError(f"Cannot start: {risk.reason}")

        strategy.status = StrategyStatus.ACTIVE.value
        self.session.commit()
        logger.info("strategy_started", name=strategy.name)
        return strategy

    def pause_strategy(self, strategy_id: int) -> Strategy:
        strategy = self.session.get(Strategy, strategy_id)
        if not strategy:
            raise ValueError("Strategy not found")
        strategy.status = StrategyStatus.PAUSED.value
        self.session.commit()
        logger.info("strategy_paused", name=strategy.name)
        return strategy

    def stop_strategy(self, strategy_id: int) -> Strategy:
        strategy = self.session.get(Strategy, strategy_id)
        if not strategy:
            raise ValueError("Strategy not found")
        strategy.status = StrategyStatus.STOPPED.value
        self.session.commit()
        return strategy

    def update_strategy(self, strategy_id: int, data: dict) -> Strategy:
        strategy = self.session.get(Strategy, strategy_id)
        if not strategy:
            raise ValueError("Strategy not found")
        for key, value in data.items():
            if value is not None and hasattr(strategy, key):
                setattr(strategy, key, value)
        self.session.commit()
        self.session.refresh(strategy)
        return strategy

    def export_to_profit(self, strategy_id: int) -> str:
        strategy = self.session.get(Strategy, strategy_id)
        if not strategy or not strategy.ntsl_code:
            raise ValueError("Strategy or NTSL code missing")
        path = self.profit.export_ntsl_strategy(strategy.name, strategy.ntsl_code)
        return str(path)
