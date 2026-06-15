"""Process-wide kill switch — blocks idea confirm and execute (A2.6c)."""

from __future__ import annotations

from datetime import datetime

_active: bool = False
_activated_at: datetime | None = None
_reason: str = ""


def is_active() -> bool:
    return _active


def status() -> dict:
    return {
        "active": _active,
        "activated_at": _activated_at.isoformat() if _activated_at else None,
        "reason": _reason or None,
    }


def set_active(active: bool, reason: str = "") -> dict:
    global _active, _activated_at, _reason
    _active = active
    if active:
        _activated_at = datetime.utcnow()
        _reason = reason.strip()
    else:
        _activated_at = None
        _reason = ""
    return status()


def ensure_not_blocked(action: str = "confirm") -> None:
    if _active:
        raise ValueError(
            f"Kill switch active — {action} blocked"
            + (f": {_reason}" if _reason else "")
        )
