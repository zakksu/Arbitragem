"""Motor journal retention — archive + prune (Release 7.0)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.config import PROJECT_ROOT, get_settings
from src.models import MotorJournal, get_engine

ARCHIVE_DIR = PROJECT_ROOT / "data" / "archives"


def ensure_journal_indexes() -> None:
    """Composite index for symbol + created_at queries."""
    engine = get_engine()
    if not str(get_settings().database_url).startswith("sqlite"):
        return
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_motor_journal_symbol_created "
                "ON motor_journal (symbol, created_at)"
            )
        )
        conn.commit()


def prune_motor_journal(session: Session, *, retention_days: int | None = None) -> dict[str, Any]:
    """Archive rows older than retention_days, then delete from hot table."""
    settings = get_settings()
    days = retention_days if retention_days is not None else settings.motor_journal_retention_days
    cutoff = datetime.utcnow() - timedelta(days=max(1, days))

    rows = (
        session.query(MotorJournal)
        .filter(MotorJournal.created_at < cutoff)
        .order_by(MotorJournal.id.asc())
        .limit(5000)
        .all()
    )
    if not rows:
        return {"archived": 0, "deleted": 0, "cutoff": cutoff.isoformat()}

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = ARCHIVE_DIR / f"motor_journal_{stamp}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(
                json.dumps(
                    {
                        "id": row.id,
                        "phase": row.phase,
                        "level": row.level,
                        "message": row.message,
                        "symbol": row.symbol,
                        "idea_id": row.idea_id,
                        "meta": row.meta,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                    },
                    default=str,
                )
                + "\n"
            )

    ids = [r.id for r in rows]
    deleted = (
        session.query(MotorJournal)
        .filter(MotorJournal.id.in_(ids))
        .delete(synchronize_session=False)
    )
    session.commit()
    return {"archived": len(rows), "deleted": deleted, "archive_file": str(path.name), "cutoff": cutoff.isoformat()}
