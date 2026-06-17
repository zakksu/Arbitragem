"""Engine Mind — aggregated motor/orchestrator state for 10.0 cockpit UI."""

from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from src.autonomous.engine_mind import get_engine_mind
from src.services.autonomy import autonomy_status
from src.services.motor_journal import PHASES, list_today
from src.services.ops_panel import get_motor_cycle_ms, motor_cycle_p95_ms
from src.services.risk_cockpit import build_risk_cockpit
from src.services.trading_orchestrator import orchestrator_status


def _motor_sources(session: Session, backend: dict[str, Any]) -> list[dict[str, Any]]:
    """At most 5 decision sources for the mind panel."""
    cockpit = build_risk_cockpit(session)
    orch = orchestrator_status()
    auto = autonomy_status()
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
    toggles = backend.get("sources") or {}
    if toggles.get("replay_training"):
        sources.append(
            {
                "id": "replay",
                "label": "Replay training",
                "kind": "train",
                "status": "ok",
                "detail": f"{backend.get('resources', {}).get('replay_workers', 1)} worker(s)",
            }
        )
    elif orch.get("last_scan_ran"):
        sources.append(
            {
                "id": "scan",
                "label": "Pattern scan",
                "kind": "scan",
                "status": "ok",
                "detail": f"+{orch.get('last_ideas_generated') or 0} ideas last cycle",
            }
        )
    if toggles.get("strategy_store"):
        sources.append(
            {
                "id": "strategies",
                "label": "Strategy store",
                "kind": "ntsl",
                "status": "ok",
                "detail": "NTSL index active",
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
    elif orch.get("motor_session_open"):
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


def _merge_breakdown(journal_counts: Counter[str], backend: dict[str, Any]) -> list[dict[str, Any]]:
    backend_bd = backend.get("cycle_breakdown") or {}
    merged: Counter[str] = Counter(journal_counts)
    for phase, count in backend_bd.items():
        merged[phase.upper()] += int(count)
    total = sum(merged.values()) or 1
    rows = [
        {
            "phase": p,
            "count": merged.get(p, 0),
            "pct": round(100.0 * merged.get(p, 0) / total, 1),
        }
        for p in PHASES
        if merged.get(p, 0) > 0
    ]
    if not rows:
        for phase, count in backend_bd.items():
            rows.append(
                {
                    "phase": phase.upper(),
                    "count": count,
                    "pct": round(100.0 * count / total, 1),
                }
            )
    if not rows:
        rows = [{"phase": "OBSERVE", "count": 0, "pct": 100.0}]
    return rows[:8]


def build_engine_mind(session: Session) -> dict[str, Any]:
    backend = get_engine_mind().snapshot()
    orch = orchestrator_status()
    auto = autonomy_status()
    journal = list_today(session, limit=40)

    counts = Counter(r.get("phase") or "OBSERVE" for r in journal)
    phase_breakdown = _merge_breakdown(counts, backend)

    current = journal[-1] if journal else None
    thinking = current["message"] if current else "Standing by — enable sleeves to start motor."
    if backend.get("last_error"):
        thinking = f"Engine: {backend['last_error']}"
    elif orch.get("last_errors"):
        thinking = f"Last issue: {orch['last_errors'][0]}"

    backend_phase = (backend.get("phase") or "idle").upper()
    current_phase = current["phase"] if current else backend_phase

    return {
        "orchestrator": orch,
        "autonomy": auto,
        "backend": backend,
        "journal": journal[-12:],
        "recent_cycles": backend.get("recent_cycles") or [],
        "phase_breakdown": phase_breakdown,
        "sources": _motor_sources(session, backend),
        "current_phase": current_phase,
        "current_symbol": current.get("symbol") if current else None,
        "thinking": thinking[:240],
        "motor_cycle_ms": get_motor_cycle_ms(),
        "motor_cycle_p95_ms": motor_cycle_p95_ms(),
        "active": bool(orch.get("active")) or backend_phase not in ("IDLE", "ERROR"),
        "resources": backend.get("resources") or {},
    }
