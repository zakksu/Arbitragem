"""Phase C gate — paper journal proof before DLL auto-live (13.0)."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.models import MotorJournal, Trade, TradeIdea


def evaluate_phase_c_gate(session: Session | None = None) -> dict[str, Any]:
    """Return pass/fail + criteria snapshot for Live Radar ready_to_execute."""
    settings = get_settings()
    if settings.phase_c_signed_off:
        return {
            "passed": True,
            "signed_off": True,
            "criteria": {"manual_signoff": True},
            "blocker": None,
        }

    if session is None:
        from src.models import get_session_factory, init_db

        init_db()
        db = get_session_factory()()
        try:
            return evaluate_phase_c_gate(db)
        finally:
            db.close()

    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    motor_days = _distinct_motor_days(session)
    motor_errors = (
        session.query(MotorJournal)
        .filter(MotorJournal.created_at >= today_start - timedelta(days=30))
        .filter(MotorJournal.level == "error")
        .count()
    )
    motor_total = (
        session.query(MotorJournal)
        .filter(MotorJournal.created_at >= today_start - timedelta(days=30))
        .count()
    )
    error_pct = (motor_errors / motor_total * 100.0) if motor_total else 100.0

    fills = (
        session.query(MotorJournal)
        .filter(MotorJournal.phase == "FILL")
        .count()
    )
    executed = (
        session.query(TradeIdea)
        .filter(TradeIdea.status == "executed")
        .count()
    )
    trade_rows = session.query(Trade).count()

    criteria = {
        "paper_sessions_days": {
            "ok": motor_days >= settings.phase_c_min_paper_days,
            "value": motor_days,
            "target": settings.phase_c_min_paper_days,
        },
        "motor_error_rate_pct": {
            "ok": error_pct < settings.phase_c_max_motor_error_pct,
            "value": round(error_pct, 2),
            "target": settings.phase_c_max_motor_error_pct,
        },
        "executed_fills": {
            "ok": max(executed, fills, trade_rows) >= settings.phase_c_min_executed_fills,
            "value": max(executed, fills, trade_rows),
            "target": settings.phase_c_min_executed_fills,
        },
        "dll_available": {
            "ok": settings.profit_bridge_enabled,
            "value": settings.profit_bridge_enabled,
        },
        "not_paper_mode": {
            "ok": not settings.paper_trading_mode,
            "value": settings.paper_trading_mode,
        },
    }
    passed = all(c["ok"] for c in criteria.values())
    blocker = None if passed else "phase_c_gate"
    return {"passed": passed, "signed_off": False, "criteria": criteria, "blocker": blocker}


def _distinct_motor_days(session: Session) -> int:
    rows = session.query(MotorJournal.created_at).all()
    days = {r[0].date() for r in rows if r[0]}
    return len(days)
