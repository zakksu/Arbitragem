"""Live Radar — single glance stack health (12.0 GA)."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from src import __version__
from src.config import PROJECT_ROOT, get_settings


def _lamp(state: str, detail: str = "", **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"state": state, "detail": detail}
    out.update(extra)
    return out


def _read_outbox() -> dict[str, Any]:
    path = PROJECT_ROOT / "data" / "profit_outbox" / "next_order.json"
    if not path.exists():
        return {"pending": False, "last_ticket": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        age_sec: float | None = None
        mtime = path.stat().st_mtime
        age_sec = round(time.time() - mtime, 1)
        return {
            "pending": True,
            "last_ticket": data,
            "chart_trading_hint": data.get("chart_trading_hint"),
            "symbol": data.get("symbol"),
            "side": data.get("side"),
            "quantity": data.get("quantity"),
            "age_sec": age_sec,
        }
    except (json.JSONDecodeError, OSError):
        return {"pending": False, "last_ticket": None, "error": "invalid_outbox"}


def _bridge_meta() -> dict[str, Any]:
    settings = get_settings()
    try:
        import httpx

        with httpx.Client(timeout=2.0) as c:
            r = c.get(f"{settings.profit_bridge_url.rstrip('/')}/health")
            if r.status_code == 200:
                body = r.json()
                mode = str(body.get("mode") or body.get("dll_mode") or "unknown").lower()
                return {
                    "ok": True,
                    "mode": mode,
                    "dll_mode": body.get("dll_mode") or body.get("mode", "stub"),
                    "is_paper": body.get("is_paper"),
                    "account_profile": body.get("account_profile"),
                    "version": body.get("version"),
                    "is_stub": mode in ("stub", "mock", "offline"),
                }
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:80]}
    return {"ok": False}


def _scan_stale(session: Session | None, *, max_age_minutes: int = 15) -> bool:
    if session is None:
        try:
            from src.models import ScanResult, get_session_factory, init_db

            init_db()
            session = get_session_factory()()
            try:
                return _scan_stale(session, max_age_minutes=max_age_minutes)
            finally:
                session.close()
        except Exception:
            return True
    from sqlalchemy import desc

    from src.models import ScanResult

    latest = session.query(ScanResult.scan_date).order_by(desc(ScanResult.scan_date)).first()
    if not latest or not latest[0]:
        return True
    age = datetime.utcnow() - latest[0]
    return age > timedelta(minutes=max_age_minutes)


def _circuit_open(healing: dict[str, Any]) -> bool:
    circuits = healing.get("circuit_breakers") or []
    items = circuits.values() if isinstance(circuits, dict) else circuits
    for val in items:
        if isinstance(val, dict) and val.get("open"):
            return True
    return False


def _mind_lamp() -> dict[str, Any]:
    try:
        from src.autonomous.engine_mind import get_engine_mind
        from src.services.trading_orchestrator import orchestrator_status

        mind = get_engine_mind().snapshot()
        orch = orchestrator_status()
        phase = str(mind.get("phase") or "idle").upper()
        active = bool(orch.get("active")) or phase not in ("IDLE", "ERROR")
        if phase == "ERROR":
            return _lamp("red", phase, phase=phase)
        if active:
            return _lamp("green", phase, phase=phase)
        return _lamp("yellow", phase, phase=phase)
    except Exception as exc:
        return _lamp("yellow", str(exc)[:40])


def build_live_radar(session: Session | None = None) -> dict[str, Any]:
    """Aggregate six lamps + readiness flags for Hybrid Cockpit Live Radar."""
    settings = get_settings()
    from src.integrations.profit_bridge import get_profit_client
    from src.services.ops_panel import motor_cycle_p95_ms
    from src.services.self_healing.health_registry import health_snapshot
    from src.services.trading_orchestrator import orchestrator_status
    from src.services.trading_sleeves import status as sleeves_status

    bridge = _bridge_meta()
    profit_ok = get_profit_client().is_available()
    orch = orchestrator_status()
    sleeve_payload = sleeves_status()
    sleeves = sleeve_payload.get("sleeves") or {}
    sym_count = len(settings.scanner_symbol_list)
    healing = health_snapshot()
    scan_stale = _scan_stale(session)

    api_ok = bool(healing.get("components", {}).get("api", True))
    p95 = motor_cycle_p95_ms()
    if not api_ok:
        api_lamp = _lamp("red", "offline")
    elif p95 is not None and p95 > 8000:
        api_lamp = _lamp("yellow", f"slow p95 {int(p95)}ms")
    else:
        api_lamp = _lamp("green", __version__)

    if profit_ok and bridge.get("ok"):
        if bridge.get("is_stub"):
            bridge_lamp = _lamp(
                "yellow",
                str(bridge.get("dll_mode") or "stub"),
                dll_mode=bridge.get("dll_mode"),
                is_paper=bridge.get("is_paper"),
            )
        else:
            bridge_lamp = _lamp(
                "green",
                str(bridge.get("dll_mode") or bridge.get("mode", "ok")),
                dll_mode=bridge.get("dll_mode"),
                is_paper=bridge.get("is_paper"),
            )
    elif profit_ok:
        bridge_lamp = _lamp("yellow", "reachable")
    else:
        bridge_lamp = _lamp("red", str(bridge.get("error") or "unreachable"))

    motor_active = bool(orch.get("active"))
    last_run = orch.get("last_run")
    motor_age: float | None = None
    if last_run:
        try:
            if isinstance(last_run, str):
                dt = datetime.fromisoformat(last_run.replace("Z", ""))
                motor_age = time.time() - dt.timestamp()
        except (TypeError, ValueError):
            motor_age = None

    circuit_open = _circuit_open(healing)
    if circuit_open or (not motor_active and not settings.paper_trading_mode):
        motor_lamp = _lamp("red", "paused" if not motor_active else "circuit open")
    elif motor_active and motor_age is not None and motor_age < 120:
        motor_lamp = _lamp("green", f"cycle {int(motor_age)}s ago", last_cycle_age_sec=int(motor_age))
    elif motor_active:
        motor_lamp = _lamp("yellow", "active, stale cycle")
    else:
        motor_lamp = _lamp("yellow", "idle but enabled")

    scanner_mode = "golden_path" if settings.golden_path_mode else settings.scanner_mode
    if sym_count == 0:
        scanner_lamp = _lamp("red", "0 symbols", symbol_count=0, mode=scanner_mode)
    elif settings.golden_path_mode and sym_count == 1:
        scanner_lamp = _lamp(
            "yellow",
            f"{sym_count} symbol",
            symbol_count=sym_count,
            mode=scanner_mode,
        )
    elif scan_stale:
        scanner_lamp = _lamp(
            "yellow",
            f"{sym_count} sym, scan stale",
            symbol_count=sym_count,
            mode=scanner_mode,
        )
    else:
        scanner_lamp = _lamp(
            "green",
            f"{sym_count} symbols",
            symbol_count=sym_count,
            mode=scanner_mode,
        )

    mind_lamp = _mind_lamp()
    if healing.get("degraded") and mind_lamp["state"] != "red":
        mind_lamp = _lamp("red", "degraded", phase=mind_lamp.get("phase"))

    cash = bool(sleeves.get("cash", True))
    opt = bool(sleeves.get("options", True))
    pairs = bool(sleeves.get("pairs", True))
    open_count = sum((cash, opt, pairs))
    if open_count == 3:
        sleeves_lamp = _lamp("green", "CASH OPT PAIR", cash=cash, options=opt, pairs=pairs)
    elif open_count == 0:
        sleeves_lamp = _lamp("red", "all closed", cash=cash, options=opt, pairs=pairs)
    else:
        sleeves_lamp = _lamp("yellow", "partial pause", cash=cash, options=opt, pairs=pairs)

    lamps = {
        "api": api_lamp,
        "bridge": bridge_lamp,
        "motor": motor_lamp,
        "scanner": scanner_lamp,
        "mind": mind_lamp,
        "sleeves": sleeves_lamp,
    }
    all_green = all(l["state"] == "green" for l in lamps.values())

    blockers: list[str] = []
    if not api_ok:
        blockers.append("api_offline")
    if not profit_ok:
        blockers.append("profit_bridge_offline")
    if not motor_active:
        blockers.append("motor_idle")
    if settings.paper_trading_mode:
        blockers.append("paper_trading_mode")

    from src.services.phase_c_gate import evaluate_phase_c_gate

    phase_c = evaluate_phase_c_gate(session)
    if not phase_c.get("passed"):
        blockers.append("phase_c_gate")

    if healing.get("degraded"):
        blockers.append("degraded_mode")
    if open_count == 0:
        blockers.append("sleeves_all_closed")
    elif not cash:
        blockers.append("cash_sleeve_paused")

    outbox = _read_outbox()
    from src.services.profit_execution_ladder import build_ladder_status

    ladder = build_ladder_status()
    ready_to_scan = api_ok and profit_ok and sym_count > 0
    dll_live = profit_ok and bridge.get("ok") and not bridge.get("is_stub")
    ready_to_execute = bool(
        all_green
        and phase_c.get("passed")
        and dll_live
        and not settings.paper_trading_mode
        and cash
        and motor_active
    )

    return {
        "all_green": all_green,
        "ready_to_scan": ready_to_scan,
        "ready_to_execute": ready_to_execute,
        "ready_manual_live": ready_to_scan and all_green and not settings.paper_trading_mode and cash,
        "phase_c": phase_c,
        "lamps": lamps,
        "outbox": outbox,
        "execution_ladder": ladder,
        "blockers": blockers,
        "paper_trading_mode": settings.paper_trading_mode,
        "execution_backend": settings.execution_backend,
        "scanner_mode": scanner_mode,
        "symbol_count": sym_count,
        "motor": {
            "active": motor_active,
            "last_run": last_run,
            "last_cycle_age_sec": motor_age,
        },
        "bridge": bridge,
        "degraded": bool(healing.get("degraded")),
    }
