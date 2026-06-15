"""Structured system events for observability (3.0 GA)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.logging_config import get_logger
from src.models import SystemEvent

logger = get_logger(__name__)


def log_event(
    session: Session,
    *,
    level: str,
    component: str,
    message: str,
    details: dict | None = None,
) -> SystemEvent:
    evt = SystemEvent(
        level=level,
        component=component,
        message=message,
        details=details,
    )
    session.add(evt)
    session.flush()
    logger.info("system_event", level=level, component=component, message=message, **(details or {}))
    return evt
