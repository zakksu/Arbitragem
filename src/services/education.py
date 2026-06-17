"""Education content pack — axioms + structure blurbs (4.0-rc A4.17)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT

_AXIOMS_PATH = PROJECT_ROOT / "data" / "education" / "axioms.json"
_STRUCTURES_PATH = PROJECT_ROOT / "data" / "education" / "structures.json"


def _load_json(path: Path) -> dict | list:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def list_axioms() -> list[dict[str, Any]]:
    data = _load_json(_AXIOMS_PATH)
    if isinstance(data, dict):
        return list(data.get("axioms") or [])
    return list(data) if isinstance(data, list) else []


def daily_axiom() -> dict[str, Any]:
    axioms = list_axioms()
    if not axioms:
        return {"title": "—", "body": "—", "pt": ""}
    idx = date.today().toordinal() % len(axioms)
    return axioms[idx]


def list_structures() -> dict[str, dict[str, Any]]:
    data = _load_json(_STRUCTURES_PATH)
    if isinstance(data, dict) and "structures" in data:
        return dict(data["structures"])
    return dict(data) if isinstance(data, dict) else {}


def structure_blurb(structure_type: str | None) -> dict[str, Any] | None:
    if not structure_type:
        return None
    key = structure_type.strip().lower()
    return list_structures().get(key)


def get_education_pack() -> dict[str, Any]:
    return {
        "axioms": list_axioms(),
        "structures": list_structures(),
        "daily_axiom": daily_axiom(),
    }
