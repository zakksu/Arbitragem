"""Health registry — probe stack components (10.0 self-healing)."""

from __future__ import annotations

import threading
import time
from typing import Any

from src.config import get_settings
from src.services.self_healing import all_breakers_snapshot, get_breaker


_registry: dict[str, Any] = {}
_lock = threading.Lock()
_degraded: bool = False


def run_health_probe() -> dict[str, Any]:
    settings = get_settings()
    components: dict[str, Any] = {}

    try:
        import httpx

        with httpx.Client(timeout=2.0) as c:
            r = c.get(f"{settings.api_base_url.rstrip('/')}/api/v1/health/live")
            components["api"] = r.status_code == 200
    except Exception:
        components["api"] = False

    from src.integrations.profit_bridge import get_profit_client

    components["profit_bridge"] = get_profit_client().is_available()

    from src.integrations.ollama_client import get_ollama_client

    components["ollama"] = get_ollama_client().is_available() if settings.ollama_runtime_enabled else None

    from src.services.knowledge.store import knowledge_status

    components["knowledge"] = knowledge_status().get("enabled", False)

    global _degraded
    if not components.get("api") or components.get("profit_bridge") is False:
        get_breaker("profit_bridge").record_failure()
        _degraded = True
    else:
        get_breaker("profit_bridge").record_success()
        _degraded = False

    snapshot = {
        "ts": time.time(),
        "components": components,
        "degraded": _degraded,
        "circuit_breakers": all_breakers_snapshot(),
    }
    with _lock:
        _registry.clear()
        _registry.update(snapshot)
    return snapshot


def health_snapshot() -> dict[str, Any]:
    with _lock:
        return dict(_registry) if _registry else {"degraded": False, "components": {}}


def is_degraded() -> bool:
    return _degraded
