"""Cached API fetches — avoids duplicate /health and alert calls every rerun."""

from __future__ import annotations

import time
from typing import Any

import streamlit as st

from dashboard.utils import api_get
from src.config import get_settings

_DEFAULT_TTL = 60
_BOOTSTRAP_TTL = 30


def _default_ttl() -> int:
    return get_settings().streamlit_cache_ttl_sec


def _cache_get(key: str) -> Any | None:
    entry = st.session_state.get(f"_api_cache_{key}")
    if not entry:
        return None
    data, expires = entry
    if time.time() > expires:
        return None
    return data


def _cache_set(key: str, data: Any, ttl: int) -> Any:
    st.session_state[f"_api_cache_{key}"] = (data, time.time() + ttl)
    return data


def cached_get(path: str, params: dict | None = None, ttl: int | None = None) -> Any:
    if ttl is None:
        ttl = _default_ttl()
    key = f"{path}|{params or {}}"
    hit = _cache_get(key)
    if hit is not None:
        return hit
    return _cache_set(key, api_get(path, params=params), ttl)


def invalidate_cache(prefix: str | None = None) -> None:
    if prefix is None:
        for k in list(st.session_state.keys()):
            if str(k).startswith("_api_cache_"):
                del st.session_state[k]
        return
    needle = prefix if prefix.startswith("/") else f"/{prefix}"
    for k in list(st.session_state.keys()):
        key = str(k)
        if not key.startswith("_api_cache_"):
            continue
        if needle in key or key.startswith(f"_api_cache_{prefix}"):
            del st.session_state[k]
    if needle in ("/health", "/account", "/scanner", "/bootstrap") or prefix == "sidebar_context":
        st.session_state.pop("_api_cache_sidebar_context", None)


def get_bootstrap(ttl: int = _BOOTSTRAP_TTL) -> dict:
    return cached_get("/bootstrap", ttl=ttl)


def get_integrations_status(ttl: int = 90) -> dict:
    """Optional — probes Ollama/Profit (up to ~3s). Not used on initial paint."""
    try:
        return cached_get("/integrations/status", ttl=ttl)
    except Exception:
        return {"ollama": False, "profit_bridge": False, "clear_api": False}


def get_health(ttl: int = 90) -> dict:
    """Legacy — prefer get_bootstrap() for dashboard shell."""
    try:
        boot = get_bootstrap(ttl=ttl)
        return {
            "status": boot.get("status", "ok"),
            "version": boot.get("version"),
            "paper_trading_mode": boot.get("paper_trading_mode"),
            "scanner_mode": boot.get("scanner_mode"),
            "scanner_symbol_count": boot.get("scanner_symbol_count"),
            "clear_api": boot.get("clear_api"),
            "ollama": None,
            "profit_bridge": None,
        }
    except Exception:
        try:
            return cached_get("/health/live", ttl=10)
        except Exception:
            return {}


def get_sidebar_context(ttl: int = _BOOTSTRAP_TTL) -> dict[str, Any]:
    """Fast shell context — single /bootstrap call, no Ollama/Profit probes."""
    cached = _cache_get("sidebar_context")
    if cached is not None:
        return cached

    try:
        boot = api_get("/bootstrap")
    except Exception as exc:
        ctx: dict[str, Any] = {
            "health": {},
            "alerts": [("critical", f"API unreachable — {exc}")],
            "account": {},
            "strategies": [],
            "scanner_alerts": [],
        }
        return _cache_set("sidebar_context", ctx, ttl=5)

    alerts: list[tuple[str, str]] = [
        (a["level"], a["message"]) for a in boot.get("alerts", [])
    ]

    integrations = _cache_get("integrations") or {}
    health = {
        "status": boot.get("status", "ok"),
        "version": boot.get("version"),
        "paper_trading_mode": boot.get("paper_trading_mode"),
        "scanner_mode": boot.get("scanner_mode"),
        "scanner_symbol_count": boot.get("scanner_symbol_count"),
        "clear_api": boot.get("clear_api"),
        "ollama": integrations.get("ollama"),
        "profit_bridge": integrations.get("profit_bridge"),
        "alerts_configured": False,
    }

    ctx = {
        "health": health,
        "alerts": alerts,
        "account": boot.get("account") or {},
        "strategies": [],
        "scanner_alerts": alerts,
        "active_strategies": boot.get("active_strategies", 0),
    }
    return _cache_set("sidebar_context", ctx, ttl)


def refresh_integrations() -> dict:
    """Manual refresh — user-triggered only."""
    invalidate_cache("/integrations/status")
    status = get_integrations_status(ttl=90)
    st.session_state["_api_cache_integrations"] = (status, time.time() + 90)
    if "sidebar_context" in st.session_state:
        del st.session_state["_api_cache_sidebar_context"]
    return status
