"""Trader Agent — unified motor cycle with journal (Phase B)."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from src.services.motor_journal import append_journal
from src.services.ops_panel import set_motor_cycle_ms
from src.services.trading_orchestrator import (
    motor_session_open,
    orchestrator_should_run,
    run_orchestrator_cycle,
)
from src.services.risk_summary import build_risk_summary


def run_trader_cycle(session: Session) -> dict[str, Any]:
    """Single entry point for autonomous trading motor + journal."""
    t0 = time.perf_counter()
    try:
        if not orchestrator_should_run():
            append_journal(session, "OBSERVE", "Motor inactive — sleeves paused", level="skip")
            return {"skipped": "orchestrator_inactive", "active": False}

        if not motor_session_open():
            append_journal(session, "OBSERVE", "Outside session window", level="skip")
            return {"skipped": "outside_b3_window", "active": True}

        summary = build_risk_summary(session)
        if summary.get("status") == "blocked":
            append_journal(
                session,
                "GATE",
                "Daily loss limit — motor skipped",
                level="skip",
                meta={"day_pnl": summary.get("day_pnl")},
            )
            return {"skipped": "risk_blocked", "active": True, "errors": ["daily loss limit"]}

        append_journal(session, "OBSERVE", "Cycle start — sleeves open, session OK", level="info")

        result = run_orchestrator_cycle(session)

        actions = list((result.get("autonomy") or {}).get("actions") or [])
        errors = list(result.get("errors") or [])
        if result.get("scan_ran"):
            append_journal(session, "SCAN", "Daily scan completed", level="info")
        if result.get("ideas_generated"):
            append_journal(
                session,
                "SCAN",
                f"Stack +{result['ideas_generated']} ideas",
                level="info",
                meta={"count": result["ideas_generated"]},
            )

        for act in actions:
            sym = act.get("symbol") or ""
            iid = act.get("idea_id")
            kind = act.get("action", "action")
            if kind in ("confirm", "execute"):
                append_journal(
                    session,
                    "ROUTE" if kind == "execute" else "RANK",
                    f"{kind.upper()} {sym} idea #{iid}",
                    level="action",
                    symbol=sym or None,
                    idea_id=iid,
                    meta=act,
                )
            elif kind == "filled":
                append_journal(
                    session,
                    "FILL",
                    f"Filled {sym} idea #{iid}",
                    level="fill",
                    symbol=sym or None,
                    idea_id=iid,
                    meta=act,
                )

        for err in errors:
            append_journal(session, "SKIP", str(err)[:500], level="error")

        if result.get("skipped"):
            append_journal(
                session,
                "JOURNAL",
                f"Cycle skipped: {result['skipped']}",
                level="skip",
            )
        else:
            append_journal(
                session,
                "JOURNAL",
                f"Cycle done — {len(actions)} actions, {len(errors)} errors",
                level="info",
                meta={"actions": len(actions), "errors": len(errors)},
            )

        return result
    finally:
        set_motor_cycle_ms((time.perf_counter() - t0) * 1000.0)
