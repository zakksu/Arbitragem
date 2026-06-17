"""Journal analyzer — post-trade insights for autonomous loop."""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.orm import Session

from src.integrations.ollama_client import get_ollama_client
from src.models import Trade
from src.services.journal import JournalService


class JournalAnalyzer:
    def __init__(self, session: Session) -> None:
        self.session = session

    def analyze_recent_sync(self, *, limit: int = 5) -> list[dict[str, Any]]:
        trades = (
            self.session.query(Trade)
            .order_by(Trade.executed_at.desc())
            .limit(limit)
            .all()
        )
        client = get_ollama_client()
        out: list[dict[str, Any]] = []
        for t in trades:
            summary = f"{t.symbol} {t.side} {t.quantity}@{t.price} pnl={t.pnl}"
            note = client.analyze_trade(summary) if client.is_available() else None
            out.append(
                {
                    "trade_id": t.id,
                    "symbol": t.symbol,
                    "summary": summary,
                    "analysis": note,
                }
            )
        return out

    async def analyze_recent(self, *, limit: int = 5) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self.analyze_recent_sync, limit=limit)

    def sync_sources(self) -> int:
        return JournalService(self.session).sync_all_sources()
