"""Profit execution ladder — paper / manual outbox / NTSL / DLL auto."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT, get_settings
from src.integrations.profit_dll_detect import detect_profit_dll, probe_dll_loadable

LADDER_MODES = ("auto", "paper_stub", "manual_outbox", "ntsl_export", "dll_auto")


def _dll_ready() -> bool:
    det = detect_profit_dll()
    if not det.get("recommended"):
        return False
    probe = probe_dll_loadable(det["recommended"])
    return bool(probe.get("loadable"))


def resolve_active_mode() -> str:
    """Resolved ladder rung (never returns 'auto')."""
    settings = get_settings()
    raw = (settings.profit_exec_ladder or "auto").strip().lower()
    if raw in LADDER_MODES and raw != "auto":
        return raw

    if settings.paper_trading_mode:
        return "paper_stub"
    if _dll_ready():
        return "dll_auto"
    if raw == "ntsl_export":
        return "ntsl_export"
    return "manual_outbox"


def build_ladder_status() -> dict[str, Any]:
    """Setup wizard + GET /profit/execution-ladder."""
    settings = get_settings()
    det = detect_profit_dll()
    active = resolve_active_mode()
    probe = probe_dll_loadable(det.get("recommended"))

    rungs = [
        {
            "id": "paper_stub",
            "label": "Paper + stub",
            "description": "Instant sim fills — journal, motor, PnL",
            "active": active == "paper_stub",
            "available": True,
        },
        {
            "id": "manual_outbox",
            "label": "Manual outbox",
            "description": "Chart Trading hint — you click in Profit",
            "active": active == "manual_outbox",
            "available": bool(det.get("profitchart_exe")) or settings.profit_bridge_enabled,
        },
        {
            "id": "ntsl_export",
            "label": "NTSL export",
            "description": "Strategy file → Profit Editor import",
            "active": active == "ntsl_export",
            "available": True,
        },
        {
            "id": "dll_auto",
            "label": "DLL auto",
            "description": "ProfitDLL order API (when module installed)",
            "active": active == "dll_auto",
            "available": _dll_ready(),
        },
    ]

    return {
        "configured": settings.profit_exec_ladder,
        "active_mode": active,
        "paper_trading_mode": settings.paper_trading_mode,
        "execution_backend": settings.execution_backend,
        "profitchart_exe": det.get("profitchart_exe") or settings.profitchart_exe or None,
        "profitchart_running": det.get("profitchart_running"),
        "dll_found": det.get("found"),
        "dll_path": det.get("recommended"),
        "dll_loadable": probe.get("loadable"),
        "automation_module_missing": det.get("automation_module_missing"),
        "automation_hint": det.get("automation_hint"),
        "ntsl_on_execute": settings.profit_ntsl_on_execute,
        "manual_auto_copy": settings.profit_manual_auto_copy,
        "rungs": rungs,
        "ntsl_dir": str(PROJECT_ROOT / "exports" / "ntsl"),
        "outbox_dir": str(PROJECT_ROOT / "data" / "profit_outbox"),
        "doc": "/docs/PROFIT_EXECUTION_LADDER.md",
    }


def _open_folder(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # noqa: S606
            return True
    except OSError:
        pass
    return False


def assist_after_profit_execute(idea: dict[str, Any], fills: list[dict[str, Any]]) -> dict[str, Any]:
    """Sidecar actions after Profit bridge submit — NTSL, clipboard hint, folders."""
    settings = get_settings()
    mode = resolve_active_mode()
    assist: dict[str, Any] = {
        "mode": mode,
        "fills": len(fills),
        "chart_trading_hint": None,
        "ntsl": None,
        "opened_folders": [],
    }

    hints = [str(f.get("chart_trading_hint") or "") for f in fills if f.get("chart_trading_hint")]
    if hints:
        assist["chart_trading_hint"] = hints[-1]

    export_ntsl = mode == "ntsl_export" or (
        settings.profit_ntsl_on_execute and mode in ("manual_outbox", "dll_auto")
    )
    if export_ntsl:
        from src.services.ntsl_arm import arm_ntsl_for_idea

        assist["ntsl"] = arm_ntsl_for_idea(idea)
        if settings.profit_open_export_folder:
            ntsl_dir = PROJECT_ROOT / "exports" / "ntsl"
            if _open_folder(ntsl_dir):
                assist["opened_folders"].append(str(ntsl_dir))

    if mode == "manual_outbox" and assist.get("chart_trading_hint"):
        assist["action"] = "copy_hint_to_profit_chart_trading"
        assist["profit_account_hint"] = "Select Sim account 3368 in Profit before paste"

    pending = [f for f in fills if f.get("status") == "pending"]
    if pending and mode == "paper_stub":
        assist["warning"] = "Tickets pending but mode is paper_stub — check PAPER_TRADING_MODE"

    return assist


def read_latest_outbox_hint() -> str | None:
    path = PROJECT_ROOT / "data" / "profit_outbox" / "next_order.json"
    if not path.exists():
        return None
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("chart_trading_hint")
    except (OSError, ValueError, TypeError):
        return None
