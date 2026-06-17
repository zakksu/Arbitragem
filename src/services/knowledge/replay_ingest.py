"""Ingest replay sessions + NTSL logic into knowledge FTS (10.0 RAG spine)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.logging_config import get_logger
from src.models import ReplaySession, StoredStrategy
from src.services.knowledge.store import ingest_text

logger = get_logger(__name__)


def ingest_replay_session(session: Session, job_id: str) -> dict[str, Any]:
    """Index replay metrics as searchable chunks for Ollama RAG."""
    settings = get_settings()
    if not settings.knowledge_runtime_enabled:
        return {"ok": False, "reason": "knowledge_disabled"}

    row = session.query(ReplaySession).filter(ReplaySession.job_id == job_id).first()
    if not row:
        return {"ok": False, "reason": "session_not_found"}

    metrics = row.metrics or {}
    body = (
        f"Replay training {row.symbol} strategy={row.strategy_name} "
        f"source={row.source} fills={row.fill_count}\n"
        f"Metrics: {json.dumps(metrics, ensure_ascii=False)[:2000]}"
    )
    return ingest_text(
        source_uri=f"replay://{job_id}",
        text=body,
        title=f"Replay {row.symbol} {row.strategy_name}",
        tags=["replay", "training", row.strategy_name],
        symbols=[row.symbol],
    )


def ingest_stored_strategy(session: Session, stored_id: int) -> dict[str, Any]:
    row = session.get(StoredStrategy, stored_id)
    if not row:
        return {"ok": False, "reason": "not_found"}
    logic = row.extracted_logic or {}
    code_excerpt = (row.ntsl_code or "")[:8000]
    body = (
        f"NTSL strategy {row.name}\n"
        f"Summary: {logic.get('summary', '')}\n"
        f"Symbols: {', '.join(row.symbols or [])}\n"
        f"Structure: {', '.join(logic.get('structure_hints') or [])}\n"
        f"Inputs: {json.dumps(logic.get('inputs') or [])}\n\n"
        f"Code:\n{code_excerpt}"
    )
    return ingest_text(
        source_uri=f"ntsl://{row.id}",
        text=body,
        title=row.name,
        tags=["ntsl", "strategy"] + (row.tags or [])[:10],
        symbols=row.symbols,
    )


def ingest_all_stored_strategies(session: Session, *, limit: int = 50) -> dict[str, Any]:
    rows = (
        session.query(StoredStrategy)
        .order_by(StoredStrategy.last_scanned_at.desc())
        .limit(limit)
        .all()
    )
    ok = 0
    for row in rows:
        result = ingest_stored_strategy(session, row.id)
        if result.get("ok"):
            ok += 1
    return {"indexed": ok, "total": len(rows)}


def ingest_recent_replays(session: Session, *, limit: int = 20) -> dict[str, Any]:
    rows = (
        session.query(ReplaySession)
        .filter(ReplaySession.status == "completed")
        .order_by(ReplaySession.completed_at.desc())
        .limit(limit)
        .all()
    )
    ok = 0
    for row in rows:
        result = ingest_replay_session(session, row.job_id)
        if result.get("ok"):
            ok += 1
    return {"indexed": ok, "total": len(rows)}
