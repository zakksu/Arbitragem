"""Integration setup wizard — auto-detect connectors for 2.0."""

from __future__ import annotations

from pathlib import Path

from src import __version__
from src.config import get_settings
from src.integrations.clear_api import get_clear_client
from src.integrations.ollama_client import get_ollama_client
from src.integrations.profit_bridge import get_profit_client


def build_setup_status() -> dict:
    settings = get_settings()
    profit = get_profit_client()
    clear = get_clear_client()
    dll_path = settings.profit_dll_path.strip()
    dll_exists = bool(dll_path and Path(dll_path).exists())

    steps = [
        {
            "id": "profit_bridge",
            "label": "Profit HTTP bridge",
            "ok": profit.is_available(),
            "detail": settings.profit_bridge_url,
            "action": "Run python scripts/profit_bridge_stub.py on Windows PC",
        },
        {
            "id": "profit_dll",
            "label": "ProfitDLL file",
            "ok": dll_exists,
            "detail": dll_path or "PROFIT_DLL_PATH not set",
            "action": "Install ProfitChart; set PROFIT_DLL_PATH in .env",
        },
        {
            "id": "clear_api",
            "label": "Clear Smart Trader API",
            "ok": clear.is_configured(),
            "detail": "Live" if clear.is_configured() else "Mock / paper mode",
            "action": "Add CLEAR_API_KEY, CLEAR_API_SECRET, CLEAR_ACCOUNT_ID",
        },
        {
            "id": "ollama",
            "label": "Ollama AI",
            "ok": get_ollama_client().is_available() if settings.ollama_enabled else False,
            "detail": settings.ollama_model if settings.ollama_enabled else "disabled",
            "action": "ollama serve && ollama pull llama3.2",
        },
    ]

    ready_live = steps[0]["ok"] and steps[2]["ok"] and not settings.paper_trading_mode

    return {
        "version": settings.app_env,
        "release": __version__,
        "paper_trading_mode": settings.paper_trading_mode,
        "scanner_mode": settings.scanner_mode,
        "execution_backend": settings.execution_backend,
        "steps": steps,
        "ready_for_paper": steps[0]["ok"] or True,
        "ready_for_live": ready_live,
        "backtest_gates": {
            "min_profit_factor": settings.backtest_min_profit_factor,
            "max_drawdown_pct": settings.backtest_max_drawdown_pct,
        },
        "docs": {
            "clear": "docs/INTEGRATIONS_WIZARD.md",
            "profit": "docs/profit_bridge.md",
            "wizard": "docs/INTEGRATIONS_WIZARD.md",
        },
    }


def run_setup_tests() -> dict:
    profit = get_profit_client()
    clear = get_clear_client()
    sample = profit.get_quote("PETR4")
    chain = profit.get_bova_option_chain()
    return {
        "profit": {
            "available": profit.is_available(),
            "sample": {"symbol": sample.symbol, "last": sample.last} if sample else None,
        },
        "clear": {
            "configured": clear.is_configured(),
            "mock_mode": not clear.is_configured(),
            "account": clear.get_account_summary(),
        },
        "bova_chain_strikes": len(chain.get("calls", [])) + len(chain.get("puts", [])),
    }
