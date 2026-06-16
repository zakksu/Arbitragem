"""Bottom pulse rail feeds — news, calendar, lessons stubs (4.0-beta)."""

from __future__ import annotations

import json
from pathlib import Path

from src.config import PROJECT_ROOT

_EDU_PATH = PROJECT_ROOT / "data" / "education" / "axioms.json"


def _load_axioms() -> list[dict]:
    if _EDU_PATH.is_file():
        try:
            data = json.loads(_EDU_PATH.read_text(encoding="utf-8"))
            return list(data.get("axioms") or data) if isinstance(data, dict) else list(data)
        except (json.JSONDecodeError, OSError):
            pass
    return [
        {
            "title": "Mean reversion",
            "body": "Extreme moves toward VWAP often fade in liquid Core14 names.",
            "pt": "Reversão à média",
        },
        {
            "title": "Risk first",
            "body": "Size from stop distance — never from hope.",
            "pt": "Risco primeiro",
        },
    ]


def get_pulse_rail() -> dict:
    axioms = _load_axioms()
    lesson = axioms[0] if axioms else {"title": "—", "body": "—"}
    return {
        "news": {
            "headline": "B3 session — Core14 liquidity normal",
            "summary": "No major macro surprise in last hour; sector pairs active.",
        },
        "calendar": {
            "events": [
                {"time": "14:30", "label": "US CPI (stub)", "impact": "high"},
                {"time": "18:00", "label": "BCB Copom minutes (stub)", "impact": "medium"},
            ],
        },
        "lesson": lesson,
        "axioms_count": len(axioms),
    }
