"""Outbound alerts — Telegram and Discord webhooks for scanner and risk events."""

from __future__ import annotations

import httpx

from src.config import get_settings
from src.logging_config import get_logger
from src.models import ScanResult

logger = get_logger(__name__)


class AlertService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return self.settings.alerts_enabled and (
            bool(self.settings.telegram_bot_token and self.settings.telegram_chat_id)
            or bool(self.settings.discord_webhook_url)
        )

    def notify(self, title: str, body: str, level: str = "info") -> None:
        if not self.settings.alerts_enabled:
            return
        message = f"*{title}*\n{body}" if level != "info" else f"{title}\n{body}"
        self._send_telegram(message)
        self._send_discord(f"**{title}**\n{body}", level)

    def notify_scan_alerts(self, results: list[ScanResult]) -> int:
        sent = 0
        for r in results:
            if r.alert_level not in ("warning", "critical"):
                continue
            tags = ", ".join(r.pattern_tags or [])
            body = (
                f"Symbol: {r.symbol}\n"
                f"Spike: {r.spike_score or 0:.0f}\n"
                f"Volume: {r.volume or 0:,}\n"
                f"Patterns: {tags or 'n/a'}"
            )
            self.notify(f"Scanner {r.alert_level.upper()}", body, r.alert_level)
            sent += 1
        return sent

    def _send_telegram(self, text: str) -> None:
        token = self.settings.telegram_bot_token
        chat_id = self.settings.telegram_chat_id
        if not token or not chat_id:
            return
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            with httpx.Client(timeout=15.0) as client:
                client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
        except Exception as exc:
            logger.warning("telegram_alert_failed", error=str(exc))

    def _send_discord(self, content: str, level: str) -> None:
        url = self.settings.discord_webhook_url
        if not url:
            return
        color = {"info": 3447003, "warning": 16776960, "critical": 15158332}.get(level, 3447003)
        try:
            with httpx.Client(timeout=15.0) as client:
                client.post(url, json={"embeds": [{"title": "Arbitragem Alert", "description": content, "color": color}]})
        except Exception as exc:
            logger.warning("discord_alert_failed", error=str(exc))


def get_alert_service() -> AlertService:
    return AlertService()
