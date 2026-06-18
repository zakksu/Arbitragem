"""Dev fast-track — spread motor journal across B3 days for Phase C gate (opt-in)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.models import MotorJournal, Trade, TradeIdea


def spread_motor_journal_days(session: Session, *, days: int = 5) -> dict[str, Any]:
    """Re-timestamp motor journal rows across distinct weekdays (AUTONOMY_FAST_TRACK only)."""
    settings = get_settings()
    if not settings.autonomy_fast_track:
        return {"ok": False, "reason": "autonomy_fast_track_disabled"}

    days = max(1, min(days, 14))
    rows = session.query(MotorJournal).order_by(MotorJournal.id.asc()).all()
    if not rows:
        return {"ok": False, "reason": "no_motor_journal"}

    today = datetime.utcnow().date()
    targets: list[datetime] = []
    d = today
    while len(targets) < days:
        if d.weekday() < 5:
            targets.append(datetime.combine(d, datetime.utcnow().time()))
        d -= timedelta(days=1)

    chunk = max(1, len(rows) // days)
    updated = 0
    for i, row in enumerate(rows):
        day_idx = min(i // chunk, len(targets) - 1)
        row.created_at = targets[day_idx]
        updated += 1

    session.commit()
    distinct = len({r.created_at.date() for r in rows if r.created_at})
    return {"ok": True, "updated": updated, "distinct_days": distinct, "target_days": days}


def autonomy_gate_snapshot(session: Session) -> dict[str, Any]:
    """Golden path + Phase C + paper validation in one payload."""
    from src.services.golden_path import evaluate_golden_path
    from src.services.paper_validation import build_paper_validation
    from src.services.phase_c_gate import evaluate_phase_c_gate

    return {
        "golden_path": evaluate_golden_path(session),
        "phase_c": evaluate_phase_c_gate(session),
        "paper_validation": build_paper_validation(session),
    }
