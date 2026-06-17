"""Motor journal — append-only log of trader agent phases (Phase B)."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from sqlalchemy.orm import Session

from src.models import MotorJournal

PHASES = (
    "OBSERVE",
    "SCAN",
    "RANK",
    "SIZE",
    "GATE",
    "ROUTE",
    "FILL",
    "JOURNAL",
    "SKIP",
)


def append_journal(
    session: Session,
    phase: str,
    message: str,
    *,
    level: str = "info",
    symbol: str | None = None,
    idea_id: int | None = None,
    meta: dict[str, Any] | None = None,
    commit: bool = True,
) -> MotorJournal:
    row = MotorJournal(
        phase=phase.upper()[:20],
        level=level[:12],
        message=message[:2000],
        symbol=(symbol or "")[:16] or None,
        idea_id=idea_id,
        meta=meta,
    )
    session.add(row)
    if commit:
        session.commit()
    return row


def list_recent(session: Session, *, limit: int = 40) -> list[dict[str, Any]]:
    rows = (
        session.query(MotorJournal)
        .order_by(MotorJournal.id.desc())
        .limit(limit)
        .all()
    )
    out: list[dict[str, Any]] = []
    for r in reversed(rows):
        out.append(
            {
                "id": r.id,
                "phase": r.phase,
                "level": r.level,
                "message": r.message,
                "symbol": r.symbol,
                "idea_id": r.idea_id,
                "meta": r.meta,
                "time": r.created_at.strftime("%H:%M:%S") if r.created_at else "",
            }
        )
    return out


def list_today(session: Session, *, limit: int = 80) -> list[dict[str, Any]]:
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    rows = (
        session.query(MotorJournal)
        .filter(MotorJournal.created_at >= today_start)
        .order_by(MotorJournal.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "phase": r.phase,
            "level": r.level,
            "message": r.message,
            "symbol": r.symbol,
            "idea_id": r.idea_id,
            "meta": r.meta,
            "time": r.created_at.strftime("%H:%M:%S") if r.created_at else "",
        }
        for r in reversed(rows)
    ]
