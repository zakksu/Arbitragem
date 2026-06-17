"""Ollama client for strategy suggestions, journal analysis, and NTSL optimization."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert Brazilian **IBOV cash equities scalper** for Filipe.
Focus on **short trades** (seconds to a few minutes). Prefer reliable tape patterns over hype.
Stocks: PETR4, VALE3, banks, BOVA11, top 20 IBOV by volume — not options unless asked.
Always give: entry trigger, stop (ticks), target (ticks), max contracts, and when NOT to trade.
Safety first: daily loss limits, no overnight, no averaging losers.
Use ProfitChart/NTSL when suggesting automation. Be concise and actionable.
"""


class OllamaClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.ollama_base_url.rstrip("/")
        self.model = self.settings.ollama_model
        self.timeout = self.settings.ollama_timeout_seconds

    def is_available(self) -> bool:
        if not self.settings.ollama_runtime_enabled:
            return False
        if self.settings.app_env == "test":
            return False
        try:
            timeout = self.settings.ollama_probe_timeout_seconds
            with httpx.Client(timeout=timeout) as client:
                r = client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    def chat(self, user_message: str, context: str | None = None) -> str:
        if not self.settings.ollama_runtime_enabled:
            return "Ollama disabled in low-RAM mode."
        prompt = user_message
        if context:
            prompt = f"Context:\n{context}\n\nUser request:\n{user_message}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        "stream": False,
                    },
                )
                r.raise_for_status()
                return r.json()["message"]["content"]
        except Exception as exc:
            logger.error("ollama_chat_failed", error=str(exc))
            return (
                f"[Ollama offline — start with `ollama serve` and pull `{self.model}`]\n"
                f"Your question was saved. Error: {exc}"
            )

    def analyze_trade(self, trade_summary: str) -> str:
        return self.chat(
            "Analyze this trade for mistakes, execution quality, and one improvement.",
            context=trade_summary,
        )

    def suggest_strategy_from_scan(self, scan_data: dict[str, Any]) -> str:
        return self.suggest_scalp_from_scan(scan_data)

    def suggest_scalp_from_scan(self, scan_data: dict[str, Any]) -> str:
        side = scan_data.get("side_bias", "neutral")
        return self.chat(
            f"Scalp setup for {scan_data.get('symbol')}: bias={side}. "
            "Give entry, exit, stop/target ticks, and 1 reliability caveat. "
            "Trade duration: seconds to minutes only.",
            context=str(scan_data),
        )

    def optimize_ntsl(self, ntsl_code: str, goal: str) -> str:
        return self.chat(
            f"Optimize this NTSL code for: {goal}. Return improved NTSL with comments.",
            context=ntsl_code,
        )


def get_ollama_client() -> OllamaClient:
    return _ollama_client_singleton()


@lru_cache(maxsize=1)
def _ollama_client_singleton() -> OllamaClient:
    return OllamaClient()
