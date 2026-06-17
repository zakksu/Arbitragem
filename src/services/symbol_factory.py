"""Symbol replication factory — shadow mode + promote gates (Release 7.0)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from src.config import PROJECT_ROOT, get_settings
from src.services.filipe_universe import load_filipe_core14
from src.services.golden_path import golden_path_summary
from src.services.ops_panel import get_process_rss_mb, read_test_status
from src.services.resource_profile import get_resource_profile

FACTORY_PATH = PROJECT_ROOT / "data" / "symbol_factory.json"
SHADOW_SESSIONS_REQUIRED = 3


def _load_state() -> dict[str, Any]:
    if not FACTORY_PATH.exists():
        return {"shadow": [], "motor": [], "promotions": []}
    try:
        data = json.loads(FACTORY_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("shadow", [])
            data.setdefault("motor", [])
            data.setdefault("promotions", [])
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"shadow": [], "motor": [], "promotions": []}


def _save_state(data: dict[str, Any]) -> None:
    FACTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.utcnow().isoformat()
    FACTORY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _factory_lock_reasons(session: Session) -> list[str]:
    settings = get_settings()
    reasons: list[str] = []
    gp = golden_path_summary(session)
    required = settings.golden_path_sessions_required
    if int(gp.get("sessions_green_count") or 0) < required:
        reasons.append(f"golden_path_sessions<{required}")
    if not gp.get("all_green"):
        reasons.append("golden_path_not_green")

    test = read_test_status()
    if test.get("state") == "red":
        reasons.append("tests_red")

    mem = get_process_rss_mb()
    budget = get_resource_profile(settings).effective_ram_budget_mb
    if mem.get("available") and float(mem.get("rss_mb") or 0) > budget:
        reasons.append("ram_over_budget")

    return reasons


def factory_candidates() -> list[dict[str, Any]]:
    settings = get_settings()
    golden = settings.golden_path_symbol.upper()
    state = _load_state()
    active = {golden} | {s["symbol"] for s in state.get("shadow", [])} | set(state.get("motor", []))
    out: list[dict[str, Any]] = []
    for sym in load_filipe_core14():
        if sym.symbol.upper() in active:
            continue
        out.append(sym.to_dict())
    return out


def factory_status(session: Session) -> dict[str, Any]:
    settings = get_settings()
    state = _load_state()
    lock_reasons = _factory_lock_reasons(session)
    return {
        "locked": bool(lock_reasons),
        "lock_reasons": lock_reasons,
        "golden_symbol": settings.golden_path_symbol,
        "shadow_symbols": state.get("shadow", []),
        "motor_symbols": [settings.golden_path_symbol, *state.get("motor", [])],
        "candidates": factory_candidates(),
        "shadow_sessions_required": SHADOW_SESSIONS_REQUIRED,
        "max_add_per_week": settings.symbol_factory_max_per_week,
        "ram_budget_mb": get_resource_profile(settings).effective_ram_budget_mb,
        "test_status": read_test_status().get("state"),
    }


def _recent_promotions(state: dict[str, Any], days: int = 7) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    count = 0
    for p in state.get("promotions") or []:
        try:
            when = datetime.fromisoformat(str(p.get("at", "")).replace("Z", ""))
            if when >= cutoff:
                count += 1
        except ValueError:
            continue
    return count


def add_shadow_symbol(session: Session, symbol: str) -> dict[str, Any]:
    sym = symbol.strip().upper()
    settings = get_settings()
    if sym == settings.golden_path_symbol:
        return {"ok": False, "error": "Cannot shadow golden path symbol"}

    lock_reasons = _factory_lock_reasons(session)
    if lock_reasons:
        return {"ok": False, "error": "Factory locked", "lock_reasons": lock_reasons}

    state = _load_state()
    if _recent_promotions(state) >= settings.symbol_factory_max_per_week:
        return {"ok": False, "error": "Max one symbol per week"}

    existing = {s["symbol"] for s in state.get("shadow", [])}
    if sym in existing:
        return {"ok": False, "error": "Already in shadow"}

    core = {s.symbol.upper() for s in load_filipe_core14()}
    if sym not in core:
        return {"ok": False, "error": "Not in Core14 template list"}

    entry = {
        "symbol": sym,
        "mode": "shadow",
        "cloned_from": settings.golden_path_symbol,
        "added_at": datetime.utcnow().isoformat(),
        "sessions_ok": 0,
        "auto_execute": False,
    }
    state.setdefault("shadow", []).append(entry)
    state.setdefault("promotions", []).append({"symbol": sym, "action": "shadow", "at": datetime.utcnow().isoformat()})
    _save_state(state)
    return {"ok": True, "shadow": entry, "status": factory_status(session)}


def promote_shadow_symbol(session: Session, symbol: str) -> dict[str, Any]:
    sym = symbol.strip().upper()
    lock_reasons = _factory_lock_reasons(session)
    if lock_reasons:
        return {"ok": False, "error": "Factory locked", "lock_reasons": lock_reasons}

    state = _load_state()
    shadow = state.get("shadow") or []
    entry = next((s for s in shadow if s.get("symbol") == sym), None)
    if not entry:
        return {"ok": False, "error": "Symbol not in shadow mode"}

    sessions_ok = int(entry.get("sessions_ok") or 0)
    if sessions_ok < SHADOW_SESSIONS_REQUIRED:
        return {
            "ok": False,
            "error": f"Shadow checklist incomplete ({sessions_ok}/{SHADOW_SESSIONS_REQUIRED} sessions)",
        }

    state["shadow"] = [s for s in shadow if s.get("symbol") != sym]
    motor = list(state.get("motor") or [])
    if sym not in motor:
        motor.append(sym)
    state["motor"] = motor
    state.setdefault("promotions", []).append({"symbol": sym, "action": "promote", "at": datetime.utcnow().isoformat()})
    _save_state(state)
    return {"ok": True, "motor_symbols": factory_status(session)["motor_symbols"]}


def record_shadow_session(symbol: str) -> None:
    """Increment shadow session counter when checklist passes (called from golden path eval)."""
    sym = symbol.strip().upper()
    state = _load_state()
    changed = False
    for entry in state.get("shadow") or []:
        if entry.get("symbol") == sym:
            entry["sessions_ok"] = int(entry.get("sessions_ok") or 0) + 1
            entry["last_session_at"] = datetime.utcnow().isoformat()
            changed = True
    if changed:
        _save_state(state)
