"""Session prep — pre-market checklist for manual + paper execution."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.config import get_settings
from src.integrations.profit_bridge import get_profit_client
from src.integrations.profit_dll_detect import detect_profit_dll
from src.services.golden_path import evaluate_golden_path
from src.services.phase_c_gate import evaluate_phase_c_gate
from src.services.profit_execution_ladder import build_ladder_status, read_latest_outbox_hint
from src.services.risk_summary import build_risk_summary
from src.services.trading_orchestrator import orchestrator_status


def _outbox_pending_count() -> int:
    from src.config import PROJECT_ROOT

    pending = PROJECT_ROOT / "data" / "profit_outbox" / "pending"
    if not pending.is_dir():
        return 0
    return len(list(pending.glob("*.json")))


def build_session_prep(session) -> dict[str, Any]:
    """Aggregate readiness for next B3 session (paper or manual Profit)."""
    settings = get_settings()
    ladder = build_ladder_status()
    det = detect_profit_dll()
    risk = build_risk_summary(session)
    phase_c = evaluate_phase_c_gate(session)
    golden = evaluate_golden_path(session)
    orch = orchestrator_status()
    bridge = get_profit_client()
    bridge_ok = bridge.is_available()

    mode = ladder["active_mode"]
    paper = settings.paper_trading_mode

    steps_pre: list[dict[str, Any]] = [
        {
            "id": "stack",
            "label": "Start stack",
            "cmd": "python scripts/dev.py start --wait",
            "ok": bridge_ok,
            "detail": settings.profit_bridge_url if bridge_ok else "API/bridge offline",
        },
        {
            "id": "session_prep",
            "label": "Run session prep",
            "cmd": "python scripts/session_prep.py",
            "ok": True,
            "detail": "This checklist",
        },
        {
            "id": "profitchart",
            "label": "ProfitChart open",
            "cmd": "Open ProfitChart manually",
            "ok": bool(det.get("profitchart_running") or det.get("profitchart_exe")),
            "detail": det.get("profitchart_exe") or "Not detected",
        },
        {
            "id": "profit_account",
            "label": "Profit account",
            "cmd": "Select Sim 3368 (paper) or Day account (live manual)",
            "ok": bool(settings.profit_password.strip()),
            "detail": "Paper Sim 3368" if paper else f"Live {settings.profit_live_style}",
        },
        {
            "id": "exec_mode",
            "label": "Execution mode",
            "cmd": f"PROFIT_EXEC_LADDER={settings.profit_exec_ladder}",
            "ok": True,
            "detail": mode,
        },
        {
            "id": "sleeves",
            "label": "CASH sleeve ON",
            "cmd": "Status bar → CASH button green",
            "ok": bool(risk.get("sleeves_all_open")),
            "detail": risk.get("sleeves_reason") or "ok",
        },
        {
            "id": "motor",
            "label": "Motor ready",
            "cmd": "Live Radar → MOTOR green",
            "ok": bool(orch.get("active") or settings.autonomy_enabled),
            "detail": "active" if orch.get("active") else "idle",
        },
    ]

    steps_during_paper: list[dict[str, str]] = [
        {"step": "1", "action": "Desk tab — watch Live Radar (aim for green lamps)"},
        {"step": "2", "action": "Let motor scan OR press Scan in toolbar"},
        {"step": "3", "action": "Review Idea Stack → Confirm top idea (two-step modal)"},
        {"step": "4", "action": "Motor auto-executes in paper — no Profit click needed"},
        {"step": "5", "action": "Journal tab — verify fill + grade"},
        {"step": "6", "action": "PnL tab — watch intraday curve"},
        {"step": "7", "action": "Stop if day P&L hits loss limit (status bar)"},
    ]

    steps_during_manual: list[dict[str, str]] = [
        {"step": "1", "action": "Set PAPER_TRADING_MODE=false + restart if doing live manual"},
        {"step": "2", "action": "ProfitChart: Sim 3368 selected, Chart Trading panel open"},
        {"step": "3", "action": "Desk → Confirm idea → Execute (or motor execute)"},
        {"step": "4", "action": "Live Radar copies hint — paste in Chart Trading (C/V Mercado · qty · sym)"},
        {"step": "5", "action": "Optional: python scripts/profit_manual_assist.py"},
        {"step": "6", "action": "Optional: import NTSL from exports/ntsl/ in Profit Editor"},
        {"step": "7", "action": "Journal tab — log matches Profit blotter"},
    ]

    blockers: list[str] = []
    if not bridge_ok:
        blockers.append("profit_bridge_offline")
    if not risk.get("sleeves_all_open"):
        blockers.append("sleeves_closed")
    if _outbox_pending_count() > 50:
        blockers.append(f"outbox_backlog_{_outbox_pending_count()}")

    ready_paper = bridge_ok and paper and risk.get("sleeves_all_open")
    ready_manual = bridge_ok and not paper and det.get("profitchart_running")

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "ready_paper_session": ready_paper,
        "ready_manual_session": ready_manual,
        "paper_trading_mode": paper,
        "active_execution_mode": mode,
        "execution_ladder": ladder,
        "phase_c": {
            "passed": phase_c.get("passed"),
            "paper_days": phase_c.get("criteria", {})
            .get("paper_sessions_days", {})
            .get("value"),
            "target_days": phase_c.get("criteria", {})
            .get("paper_sessions_days", {})
            .get("target"),
        },
        "golden_path": {
            "all_green": golden.get("all_green"),
            "sessions_green": golden.get("sessions_green_count"),
        },
        "risk": {
            "day_pnl_brl": risk.get("day_pnl"),
            "loss_limit_brl": risk.get("tightest_loss_limit_brl"),
            "can_execute": risk.get("can_execute_ideas"),
        },
        "outbox_pending": _outbox_pending_count(),
        "latest_hint": read_latest_outbox_hint(),
        "blockers": blockers,
        "steps_pre": steps_pre,
        "steps_during_paper": steps_during_paper,
        "steps_during_manual": steps_during_manual,
        "quick_commands": {
            "start": "python scripts/dev.py start --wait --open",
            "prep": "python scripts/session_prep.py",
            "assist": "python scripts/profit_manual_assist.py",
            "archive_outbox": "python scripts/archive_profit_outbox.py",
        },
        "board_url": "http://localhost:8000/board",
    }
