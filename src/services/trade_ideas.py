"""Trade idea engine — scanner v2 output for Idea Stack."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.integrations.profit_bridge import get_profit_client
from src.logging_config import get_logger
from src.models import ScanResult, TradeIdea
from src.services.filipe_universe import sector_for

logger = get_logger(__name__)


class TradeIdeaService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.profit = get_profit_client()

    def list_ideas(self, limit: int = 20, status: str | None = None) -> list[TradeIdea]:
        q = self.session.query(TradeIdea).order_by(
            desc(TradeIdea.reliability), desc(TradeIdea.created_at)
        )
        if status:
            q = q.filter(TradeIdea.status == status)
        return q.limit(limit).all()

    def generate_from_latest_scan(self, limit: int = 10) -> list[TradeIdea]:
        latest = (
            self.session.query(ScanResult.scan_date).order_by(desc(ScanResult.scan_date)).first()
        )
        if not latest:
            return []

        scans = (
            self.session.query(ScanResult)
            .filter(ScanResult.scan_date == latest[0])
            .order_by(desc(ScanResult.spike_score))
            .all()
        )
        created: list[TradeIdea] = []
        for scan in scans:
            raw = scan.raw_data or {}
            reliability = float(raw.get("reliability", 0) or 0)
            if reliability < 20 and not scan.pattern_tags:
                continue
            if len(created) >= limit:
                break

            side = str(raw.get("side_bias", "neutral")).lower()
            structure = f"scalp_{side}" if side in ("long", "short") else "scalp"
            quote = self.profit.get_quote(scan.symbol)
            last = quote.last if quote else raw.get("last")
            stop_t = int(raw.get("stop_ticks", 5))
            target_t = int(raw.get("target_ticks", 8))
            tick = 0.01 if last and last < 50 else 0.05
            entry = float(last) if last else None
            stop_p = round(entry - stop_t * tick, 4) if entry and side == "long" else (
                round(entry + stop_t * tick, 4) if entry and side == "short" else None
            )
            target_p = round(entry + target_t * tick, 4) if entry and side == "long" else (
                round(entry - target_t * tick, 4) if entry and side == "short" else None
            )

            tags = list(scan.pattern_tags or [])
            sector = sector_for(scan.symbol)
            if sector:
                tags.append(f"sector:{sector.lower()}")

            idea = TradeIdea(
                symbol=scan.symbol,
                structure_type=structure,
                side=side,
                status="detected",
                reliability=reliability,
                entry_price=entry,
                stop_price=stop_p,
                target_price=target_p,
                stop_ticks=stop_t,
                target_ticks=target_t,
                title=f"{scan.symbol} {side.upper()} scalp",
                rationale_tags=tags,
                legs=[
                    {
                        "symbol": scan.symbol,
                        "side": "buy" if side == "long" else "sell" if side == "short" else "flat",
                        "quantity": 100,
                    }
                ],
                scan_result_id=scan.id,
            )
            self.session.add(idea)
            created.append(idea)

            metrics = self.profit.run_backtest(scan.symbol)
            if self.passes_backtest_gate(metrics):
                idea.backtest_proof = metrics
                idea.status = "backtested"
                idea.rationale_tags = list(idea.rationale_tags or []) + ["backtest_pass"]

        self.session.commit()
        logger.info("trade_ideas_generated", count=len(created))
        return created

    def confirm_idea(self, idea_id: int, paper: bool = True) -> TradeIdea:
        idea = self.session.get(TradeIdea, idea_id)
        if not idea:
            raise ValueError("Idea not found")
        if idea.status in ("executed", "rejected"):
            raise ValueError(f"Idea already {idea.status}")

        from src.config import get_settings
        from src.services.risk_summary import build_risk_summary

        risk = build_risk_summary(self.session)
        if risk["status"] == "blocked":
            raise ValueError("Daily loss limit blocked — cannot confirm")

        idea.status = "confirmed"
        idea.confirmed_at = datetime.utcnow()

        settings = get_settings()
        ntsl_path = None
        if settings.execution_backend == "ntsl":
            ntsl_code = self._ntsl_for_idea(idea)
            ntsl_path = get_profit_client().export_ntsl_strategy(
                f"idea_{idea.id}_{idea.symbol}", ntsl_code
            )
            idea.rationale = (
                (idea.rationale or "")
                + f"\n[NTSL] Exported to {ntsl_path} — import in Profit Editor and arm strategy."
            )

        if paper or settings.paper_trading_mode:
            idea.status = "executed"
            idea.executed_at = datetime.utcnow()
            idea.rationale = (idea.rationale or "") + "\n[Paper] Logged — confirm NTSL in Profit for live."
            self._log_paper_trades(idea)
        elif settings.execution_backend == "clear":
            self._execute_clear_legs(idea)

        self.session.commit()
        self.session.refresh(idea)
        return idea

    @staticmethod
    def passes_backtest_gate(metrics: dict | None) -> bool:
        if not metrics:
            return False
        from src.config import get_settings

        s = get_settings()
        pf = float(metrics.get("profit_factor") or metrics.get("profitFactor") or 0)
        dd = float(
            metrics.get("max_drawdown_pct")
            or metrics.get("max_drawdown")
            or metrics.get("maxDrawdown")
            or 100
        )
        if dd <= 1.0:
            dd *= 100.0
        if pf < s.backtest_min_profit_factor:
            return False
        if dd > s.backtest_max_drawdown_pct:
            return False
        return True

    @staticmethod
    def _ntsl_for_idea(idea: TradeIdea) -> str:
        side = idea.side or "neutral"
        return f"""// Arbitragem — idea #{idea.id} {idea.symbol} ({side})
// Import in Profit Editor → arm on {idea.symbol}
input
  StopTicks({idea.stop_ticks or 5});
  TargetTicks({idea.target_ticks or 8});
begin
  // TODO: wire pattern from backtest proof — manual arm for 2.0-alpha
end;
"""

    def _log_paper_trades(self, idea: TradeIdea) -> None:
        from src.integrations.clear_api import ClearOrder, get_clear_client
        from src.models import JournalEntry, Trade

        for leg in idea.legs or []:
            side = leg.get("side", "buy")
            if side == "flat":
                continue
            qty = int(leg.get("quantity", 100))
            sym = leg.get("symbol", idea.symbol)
            price = float(idea.entry_price or 0)
            get_clear_client().place_order(ClearOrder(symbol=sym, side=side, quantity=qty))
            trade = Trade(
                external_id=f"idea-{idea.id}-{sym}-{side}",
                source="paper",
                symbol=sym,
                side=side,
                quantity=qty,
                price=price,
                fees=0.0,
                executed_at=datetime.utcnow(),
                raw_payload={"idea_id": idea.id, "legs": idea.legs},
            )
            self.session.add(trade)
        self.session.flush()
        self.session.add(
            JournalEntry(
                title=f"Idea #{idea.id} {idea.symbol}",
                content=idea.rationale or idea.title or "",
                tags=["idea", "paper", idea.structure_type],
                ai_generated=False,
            )
        )

    def _execute_clear_legs(self, idea: TradeIdea) -> None:
        from src.integrations.clear_api import ClearOrder, get_clear_client

        client = get_clear_client()
        for leg in idea.legs or []:
            side = leg.get("side", "buy")
            if side == "flat":
                continue
            client.place_order(
                ClearOrder(
                    symbol=leg.get("symbol", idea.symbol),
                    side=side,
                    quantity=int(leg.get("quantity", 100)),
                )
            )
        idea.status = "executed"
        idea.executed_at = datetime.utcnow()

    def to_dict(self, idea: TradeIdea) -> dict:
        return {
            "id": idea.id,
            "symbol": idea.symbol,
            "structure_type": idea.structure_type,
            "side": idea.side,
            "status": idea.status,
            "reliability": idea.reliability,
            "entry_price": idea.entry_price,
            "stop_price": idea.stop_price,
            "target_price": idea.target_price,
            "stop_ticks": idea.stop_ticks,
            "target_ticks": idea.target_ticks,
            "title": idea.title,
            "rationale": idea.rationale,
            "rationale_tags": idea.rationale_tags or [],
            "tags": idea.rationale_tags or [],
            "legs": idea.legs or [],
            "backtest_proof": idea.backtest_proof,
            "created_at": idea.created_at.isoformat() if idea.created_at else None,
            "confirmed_at": idea.confirmed_at.isoformat() if idea.confirmed_at else None,
            "executed_at": idea.executed_at.isoformat() if idea.executed_at else None,
        }
