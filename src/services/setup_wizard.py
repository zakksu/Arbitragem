"""Integration setup wizard — auto-detect connectors for 2.0 / 3.0.1."""

from __future__ import annotations

from pathlib import Path

from src import __version__
from src.config import get_settings
from src.integrations.clear_api import get_clear_client
from src.integrations.ollama_client import get_ollama_client
from src.integrations.profit_bridge import get_profit_client
from src.integrations.profit_dll_detect import detect_profit_dll, probe_dll_loadable
from src.services.profit_accounts import profit_account_checklist, resolve_profit_account


def _resolve_dll_path() -> tuple[str, bool, dict]:
    settings = get_settings()
    configured = settings.profit_dll_path.strip()
    if configured and Path(configured).exists():
        return configured, True, {"source": "env", "candidates": [configured]}

    detection = detect_profit_dll()
    recommended = detection.get("recommended")
    if recommended and Path(recommended).exists():
        return recommended, True, detection

    return configured, False, detection


def build_setup_status() -> dict:
    settings = get_settings()
    profit = get_profit_client()
    clear = get_clear_client()
    dll_path, dll_exists, dll_detect = _resolve_dll_path()
    profitchart = settings.profitchart_exe.strip()
    profitchart_ok = bool(profitchart and Path(profitchart).exists())
    profit_acct = resolve_profit_account(settings)

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
            "detail": dll_path or dll_detect.get("recommended") or dll_detect.get("automation_hint") or "PROFIT_DLL_PATH not set",
            "action": "Install Nelogica Módulo de Automação or set PROFIT_DLL_PATH in .env",
            "candidates": dll_detect.get("candidates", []),
            "auto_detected": dll_detect.get("source") != "env" and dll_exists,
            "profitchart_exe": dll_detect.get("profitchart_exe"),
            "automation_module_missing": dll_detect.get("automation_module_missing"),
        },
        {
            "id": "profitchart",
            "label": "ProfitChart install",
            "ok": profitchart_ok,
            "detail": profitchart or "PROFITCHART_EXE not set (optional)",
            "action": "Set PROFITCHART_EXE in .env — dev.py co-starts on Windows",
        },
        {
            "id": "profit_account",
            "label": "ProfitChart account",
            "ok": bool(settings.profit_password.strip()),
            "detail": profit_acct["display"],
            "action": "Set PROFIT_PASSWORD in .env; select matching account in Profit Chart Trading panel",
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
            "ok": get_ollama_client().is_available() if settings.ollama_runtime_enabled else False,
            "detail": settings.ollama_model if settings.ollama_runtime_enabled else "disabled",
            "action": "ollama serve && ollama pull llama3.2",
        },
        {
            "id": "autonomous_ops",
            "label": "Autonomous scheduler",
            "ok": settings.autonomous_engine_enabled and settings.autonomous_rankings_sync,
            "detail": (
                f"Rankings sync every {settings.rankings_sync_interval_hours}h · "
                f"WF promote={'on' if settings.walk_forward_auto_promote else 'off'}"
            ),
            "action": "POST /api/v1/backtest/rankings/sync or POST /api/v1/autonomous/run",
        },
    ]

    ready_live = steps[0]["ok"] and steps[3]["ok"] and not settings.paper_trading_mode

    return {
        "version": settings.app_env,
        "release": __version__,
        "paper_trading_mode": settings.paper_trading_mode,
        "scanner_mode": settings.scanner_mode,
        "execution_backend": settings.execution_backend,
        "profit_account": profit_acct,
        "profit_accounts": profit_account_checklist(settings),
        "steps": steps,
        "profit_dll_detect": {**dll_detect, "probe": probe_dll_loadable(dll_path or None)},
        "autonomous_ops": {
            "engine_enabled": settings.autonomous_engine_enabled,
            "rankings_sync": settings.autonomous_rankings_sync,
            "rankings_sync_interval_hours": settings.rankings_sync_interval_hours,
            "walk_forward_auto_promote": settings.walk_forward_auto_promote,
            "walk_forward_use_bridge_candles": settings.walk_forward_use_bridge_candles,
            "autonomy_motor_enabled": settings.autonomy_enabled,
        },
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
    account = profit.get_account_summary()
    return {
        "profit": {
            "available": profit.is_available(),
            "sample": {"symbol": sample.symbol, "last": sample.last} if sample else None,
            "account": account,
        },
        "clear": {
            "configured": clear.is_configured(),
            "mock_mode": not clear.is_configured(),
            "account": clear.get_account_summary(),
        },
        "bova_chain_strikes": len(chain.get("calls", [])) + len(chain.get("puts", [])),
    }
