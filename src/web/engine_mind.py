"""Engine Mind — aggregated motor/orchestrator state for 10.0 cockpit UI."""

from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from src.services.autonomy import autonomy_status
from src.services.motor_journal import PHASES, list_today
from src.services.ops_panel import get_motor_cycle_ms, motor_cycle_p95_ms
from src.services.risk_cockpit import build_risk_cockpit
from src.services.trading_orchestrator import orchestrator_status


def _sources(session: Session, orch: dict[str, Any], auto: dict[str, Any]) -> list[dict[str, Any]]:
    """At most 5 decision sources for the mind panel."""
    cockpit = build_risk_cockpit(session)
    sources: list[dict[str, Any]] = []

    sources.append(
        {
            "id": "risk",
            "label": "Risk cockpit",
            "kind": "gate",
            "status": cockpit.get("gate_status") or "ok",
            "detail": f"P&L R$ {cockpit.get('day_pnl', 0):.2f} · Δ {cockpit.get('net_delta', 0):+.2f}",
        }
    )
    sleeves = orch.get("sleeves") or {}
    open_n = sum(1 for v in sleeves.values() if v)
    sources.append(
        {
            "id": "sleeves",
            "label": "Trading sleeves",
            "kind": "router",
            "status": "ok" if open_n else "paused",
            "detail": f"{open_n}/3 sleeves open",
        }
    )
    if orch.get("last_scan_ran"):
        sources.append(
            {
                "id": "scan",
                "label": "Pattern scan",
                "kind": "scan",
                "status": "ok",
                "detail": f"+{orch.get('last_ideas_generated') or 0} ideas last cycle",
            }
        )
    last_auto = orch.get("last_autonomy") or {}
    actions = last_auto.get("actions") or auto.get("last_actions") or []
    if actions:
        sources.append(
            {
                "id": "autonomy",
                "label": "Autonomy cycle",
                "kind": "action",
                "status": "ok",
                "detail": f"{len(actions)} action(s) last tick",
            }
        )
    if orch.get("motor_session_open"):
        sources.append(
            {
                "id": "session",
                "label": "B3 session",
                "kind": "clock",
                "status": "open",
                "detail": "Motor window active",
            }
        )
    else:
        sources.append(
            {
                "id": "session",
                "label": "B3 session",
                "kind": "clock",
                "status": "closed",
                "detail": "Outside motor window",
            }
        )
    return sources[:5]


def build_engine_mind(session: Session) -> dict[str, Any]:
    orch = orchestrator_status()
    auto = autonomy_status()
    journal = list_today(session, limit=40)

    counts = Counter(r.get("phase") or "OBSERVE" for r in journal)
    total = sum(counts.values()) or 1
    phase_breakdown = [
        {
            "phase": p,
            "count": counts.get(p, 0),
            "pct": round(100.0 * counts.get(p, 0) / total, 1),
        }
        for p in PHASES
        if counts.get(p, 0) > 0
    ]
    if not phase_breakdown:
        phase_breakdown = [{"phase": "OBSERVE", "count": 0, "pct": 100.0}]

    current = journal[-1] if journal else None
    thinking = current["message"] if current else "Standing by — enable sleeves to start motor."
    if orch.get("last_errors"):
        thinking = f"Last issue: {orch['last_errors'][0]}"

    return {
        "orchestrator": orch,
        "autonomy": auto,
        "journal": journal[-12:],
        "phase_breakdown": phase_breakdown,
        "sources": _sources(session, orch, auto),
        "current_phase": current["phase"] if current else "OBSERVE",
        "current_symbol": current.get("symbol") if current else None,
        "thinking": thinking[:240],
        "motor_cycle_ms": get_motor_cycle_ms(),
        "motor_cycle_p95_ms": motor_cycle_p95_ms(),
        "active": bool(orch.get("active")),
    }
