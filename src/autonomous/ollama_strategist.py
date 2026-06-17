"""Ollama strategist — rankings commentary + idea promotion hints."""

from __future__ import annotations

import asyncio
from typing import Any

from src.integrations.ollama_client import get_ollama_client


class OllamaStrategist:
    """Async-friendly wrapper; runs sync Ollama in thread pool."""

    def comment_on_ranking_sync(self, ranking: dict[str, Any]) -> str:
        client = get_ollama_client()
        ctx = (
            f"Symbol: {ranking.get('symbol')}\n"
            f"WF score: {ranking.get('wf_score')}\n"
            f"PF: {ranking.get('profit_factor')}\n"
            f"DD%: {ranking.get('max_drawdown_pct')}\n"
            f"Win rate: {ranking.get('win_rate')}\n"
            f"Params: {ranking.get('parameters')}\n"
            f"Folds: {ranking.get('fold_results', [])[:3]}"
        )
        return client.chat(
            "In 3-5 bullet points: promote to live idea stack or wait? "
            "Mention risk and B3 session fit.",
            context=ctx,
        )

    async def comment_on_ranking(self, ranking: dict[str, Any]) -> str:
        return await asyncio.to_thread(self.comment_on_ranking_sync, ranking)
