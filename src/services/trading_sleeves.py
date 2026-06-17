"""Per-market-group trading sleeves — ON/OFF gates (replaces kill switch)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT

SLEEVES = ("cash", "options", "pairs")
_STATE_PATH = PROJECT_ROOT / "data" / "trading_sleeves.json"

_state: dict[str, bool] = {s: True for s in SLEEVES}
_paused_reason: str = ""
_loaded = False


def _load() -> None:
    global _state, _paused_reason, _loaded
    if _loaded:
        return
    _loaded = True
    if _STATE_PATH.exists():
        try:
            data = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
            for s in SLEEVES:
                if s in data.get("sleeves", {}):
                    _state[s] = bool(data["sleeves"][s])
            _paused_reason = str(data.get("reason") or "")
        except (json.JSONDecodeError, OSError):
            pass


def _save() -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(
        json.dumps(
            {
                "sleeves": dict(_state),
                "reason": _paused_reason,
                "updated_at": datetime.utcnow().isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _is_option_symbol(symbol: str) -> bool:
    sym = symbol.upper()
    if sym.startswith("BOVA") and sym != "BOVA11":
        return True
    # B3 equity: 4 letters + 1 digit (PETR4, VALE3)
    if len(sym) == 5 and sym[:4].isalpha() and sym[4].isdigit():
        return False
    # Stock/index options: longer tickers with strike suffix
    if len(sym) > 5 and sym[:4].isalpha():
        return any(c.isdigit() for c in sym[4:])
    return False


def sleeve_for_idea(idea: dict[str, Any]) -> str:
    """Map idea structure/tags to cash | options | pairs."""
    tags = idea.get("rationale_tags") or idea.get("tags") or []
    structure = str(idea.get("structure_type", "scalp")).lower()
    legs = idea.get("legs") or []

    if any(t == "sector_pair" for t in tags) or structure in (
        "pair_relative",
        "pair_spread",
    ):
        return "pairs"

    option_structures = {
        "covered_call",
        "vertical",
        "collar",
        "bova_hedge",
        "iron_condor",
        "straddle",
    }
    if structure in option_structures:
        return "options"

    option_legs = sum(
        1 for leg in legs if _is_option_symbol(str(leg.get("symbol", "")))
    )
    if option_legs > 1 or (option_legs >= 1 and len(legs) > 1):
        return "options"

    for leg in legs:
        sym = str(leg.get("symbol", "")).upper()
        if _is_option_symbol(sym):
            return "options"

    return "cash"


def is_open(sleeve: str) -> bool:
    _load()
    return _state.get(sleeve, True)


def status() -> dict[str, Any]:
    _load()
    return {
        "sleeves": {s: _state.get(s, True) for s in SLEEVES},
        "all_open": all(_state.get(s, True) for s in SLEEVES),
        "reason": _paused_reason or None,
    }


def set_sleeve(sleeve: str, open_: bool, *, reason: str = "") -> dict:
    _load()
    key = sleeve.lower()
    if key not in SLEEVES:
        raise ValueError(f"Unknown sleeve '{sleeve}' — use cash, options, or pairs")
    global _paused_reason
    _state[key] = open_
    if not open_ and reason:
        _paused_reason = reason.strip()
    elif all(_state.get(s, True) for s in SLEEVES):
        _paused_reason = ""
    _save()
    return status()


def set_all(open_: bool, *, reason: str = "") -> dict:
    _load()
    global _paused_reason
    for s in SLEEVES:
        _state[s] = open_
    _paused_reason = reason.strip() if not open_ else ""
    _save()
    return status()


def ensure_sleeve_open(sleeve: str, action: str = "trade") -> None:
    _load()
    key = sleeve.lower()
    if key not in SLEEVES:
        key = "cash"
    if not _state.get(key, True):
        label = key.upper()
        raise ValueError(
            f"{label} sleeve paused — {action} blocked"
            + (f": {_paused_reason}" if _paused_reason else "")
        )


def ensure_all_sleeves_open(action: str = "trade") -> None:
    _load()
    closed = [s for s in SLEEVES if not _state.get(s, True)]
    if closed:
        raise ValueError(
            f"Trading sleeves paused ({', '.join(closed)}) — {action} blocked"
            + (f": {_paused_reason}" if _paused_reason else "")
        )
