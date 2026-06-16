"""Load HelpTip copy from docs/tooltips/*.json (4.0-alpha W4.6)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TOOLTIPS_DIR = _REPO_ROOT / "docs" / "tooltips"


@lru_cache(maxsize=1)
def load_tooltips() -> dict[str, dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    if not _TOOLTIPS_DIR.is_dir():
        return merged
    for path in sorted(_TOOLTIPS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            merged.update(data)
    return merged


def get_tooltip(key: str) -> dict[str, str]:
    entry = load_tooltips().get(key, {})
    return {
        "en": entry.get("en", key),
        "pt": entry.get("pt", ""),
    }
