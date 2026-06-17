"""Knowledge poisoning guards (10.0-GA)."""

from __future__ import annotations

import re
from typing import Any

_BLOCKED_PATTERNS = (
    r"ignore\s+all\s+previous",
    r"system\s+prompt",
    r"jailbreak",
    r"<\s*script",
)


def validate_ingest_text(text: str, *, source_uri: str = "") -> dict[str, Any]:
    """Reject suspicious corpus before FTS index."""
    if len(text) > 500_000:
        return {"ok": False, "reason": "text_too_large"}
    lower = text.lower()
    for pat in _BLOCKED_PATTERNS:
        if re.search(pat, lower):
            return {"ok": False, "reason": "blocked_pattern", "pattern": pat}
    if source_uri and ".." in source_uri:
        return {"ok": False, "reason": "invalid_source_uri"}
    return {"ok": True}
