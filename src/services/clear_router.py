"""Clear live order router status — A2.6b."""

from __future__ import annotations

from typing import Any

from src.config import get_settings
from src.integrations.clear_api import get_clear_client


def clear_router_status() -> dict[str, Any]:
    settings = get_settings()
    client = get_clear_client()
    configured = client.is_configured()
    paper = settings.paper_trading_mode
    backend = (settings.execution_backend or "profit").lower()
    live_ready = configured and not paper and backend == "clear"
    return {
        "backend": backend,
        "paper_trading_mode": paper,
        "clear_configured": configured,
        "live_enabled": live_ready,
        "account_id": settings.clear_account_id or None,
        "message": (
            "Clear live routing ready"
            if live_ready
            else "Paper mode or Clear keys missing — live orders blocked"
        ),
    }
