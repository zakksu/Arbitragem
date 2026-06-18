"""Auto journal — syncs trades from Clear/Profit and adds Ollama analysis."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.config import get_settings
from src.integrations.clear_api import get_clear_client
from src.integrations.ollama_client import get_ollama_client
from src.integrations.profit_bridge import get_profit_client
from src.logging_config import get_logger
from src.models import JournalEntry, Trade

logger = get_logger(__name__)


class JournalService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.clear = get_clear_client()
        self.profit = get_profit_client()
        self.ollama = get_ollama_client()

    def sync_trades_from_clear(self) -> int:
        """Import today's trades from Clear API; skip duplicates by external_id."""
        if not self.clear.is_configured():
            logger.debug("clear_sync_skipped", reason="clear_api_key_not_configured")
            return 0
        imported = 0
        for ct in self.clear.get_trades_today():
            exists = (
                self.session.query(Trade)
                .filter(Trade.external_id == ct.external_id)
                .first()
            )
            if exists:
                continue

            trade = Trade(
                external_id=ct.external_id,
                source="clear",
                symbol=ct.symbol,
                side=ct.side,
                quantity=ct.quantity,
                price=ct.price,
                fees=ct.fees,
                executed_at=ct.executed_at,
                raw_payload=ct.raw,
            )
            self.session.add(trade)
            imported += 1

        self.session.commit()
        logger.info("trades_synced_clear", count=imported)
        return imported

    def sync_trades_from_profit(self) -> int:
        """Import today's trades from Profit bridge."""
        imported = 0
        for pt in self.profit.get_trades_today():
            ext_id = f"profit-{pt.external_id}"
            exists = (
                self.session.query(Trade)
                .filter(Trade.external_id == ext_id)
                .first()
            )
            if exists:
                continue
            self.session.add(
                Trade(
                    external_id=ext_id,
                    source="profit",
                    symbol=pt.symbol,
                    side=pt.side,
                    quantity=pt.quantity,
                    price=pt.price,
                    fees=pt.fees,
                    pnl=pt.pnl,
                    executed_at=pt.executed_at,
                    raw_payload=pt.raw,
                )
            )
            imported += 1
        self.session.commit()
        logger.info("trades_synced_profit", count=imported)
        return imported

    def sync_all_sources(self, analyze: bool | None = None) -> dict[str, int | bool]:
        clear_configured = self.clear.is_configured()
        clear_n = self.sync_trades_from_clear() if clear_configured else 0
        profit_n = self.sync_trades_from_profit()
        do_analyze = (
            analyze
            if analyze is not None
            else get_settings().journal_auto_analyze
        )
        analyzed = 0
        if do_analyze:
            analyzed = self.auto_analyze_recent_trades(
                limit=get_settings().journal_analyze_limit
            )
        return {
            "clear_configured": clear_configured,
            "imported_clear": clear_n,
            "imported_profit": profit_n,
            "imported": clear_n + profit_n,
            "analyzed": analyzed,
        }

    def auto_analyze_recent_trades(self, limit: int = 10) -> int:
        """Run Ollama analysis on trades missing ai_analysis."""
        if not self.ollama.is_available():
            return 0
        trades = (
            self.session.query(Trade)
            .filter(Trade.ai_analysis.is_(None))
            .order_by(Trade.executed_at.desc())
            .limit(limit)
            .all()
        )
        analyzed = 0
        for trade in trades:
            summary = (
                f"{trade.side} {trade.quantity} {trade.symbol} @ {trade.price} "
                f"fees={trade.fees} pnl={trade.pnl}"
            )
            trade.ai_analysis = self.ollama.analyze_trade(summary)
            self.session.add(
                JournalEntry(
                    trade_id=trade.id,
                    title=f"Auto-analysis: {trade.symbol}",
                    content=trade.ai_analysis,
                    tags=["auto", "ollama"],
                    ai_generated=True,
                )
            )
            analyzed += 1

        self.session.commit()
        return analyzed
