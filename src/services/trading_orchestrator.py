"""Trading orchestrator — scan, rank, confirm, execute when sleeves are ON."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.config import get_settings
from src.logging_config import get_logger
from src.models import ScanResult
from src.services.autonomy import run_autonomy_cycle
from src.services.risk_summary import build_risk_summary
from src.services.scanner import PatternScanner
from src.services.trade_ideas import TradeIdeaService
from src.services.trading_sleeves import SLEEVES, is_open, status as sleeves_status

logger = get_logger(__name__)

_last_run: datetime | None = None
_last_result: dict[str, Any] = {
    "active": False,
    "last_run": None,
    "scan_ran": False,
    "ideas_generated": 0,
    "autonomy": {},
    "errors": [],
}


def b3_session_open() -> bool:
    """B3 cash + pre-market orchestration window 09:00–18:30 BRT (UTC-3)."""
    now = datetime.utcnow()
    if now.weekday() >= 5:
        return False
    hour = (now.hour - 3) % 24
    minute = now.minute
    mins = hour * 60 + minute
    return 9 * 60 <= mins < 18 * 60 + 30


def motor_session_open() -> bool:
    """B3 window — paper motor can run 24/7 when configured (Sim account testing)."""
    settings = get_settings()
    if settings.paper_trading_mode and settings.paper_motor_ignore_b3_hours:
        now = datetime.utcnow()
        return now.weekday() < 5
    return b3_session_open()


def orchestrator_should_run() -> bool:
    settings = get_settings()
    if not any(is_open(s) for s in SLEEVES):
        return False
    if settings.paper_trading_mode and settings.auto_trading_on_sleeves:
        return True
    return settings.autonomy_enabled


def orchestrator_status() -> dict[str, Any]:
    settings = get_settings()
    return {
        "active": orchestrator_should_run(),
        "paper_auto": settings.paper_trading_mode and settings.auto_trading_on_sleeves,
        "autonomy_enabled": settings.autonomy_enabled,
        "b3_session_open": b3_session_open(),
        "motor_session_open": motor_session_open(),
        "paper_capital_brl": settings.paper_capital_brl,
        "sleeves": sleeves_status(),
        "interval_sec": settings.orchestrator_interval_sec,
        "last_run": _last_result.get("last_run"),
        "last_scan_ran": _last_result.get("scan_ran"),
        "last_ideas_generated": _last_result.get("ideas_generated"),
        "last_autonomy": _last_result.get("autonomy"),
        "last_errors": _last_result.get("errors", []),
    }


def _scan_is_stale(session: Session, *, max_age_minutes: int = 20) -> bool:
    latest = session.query(ScanResult.scan_date).order_by(desc(ScanResult.scan_date)).first()
    if not latest or not latest[0]:
        return True
    age = datetime.utcnow() - latest[0]
    return age > timedelta(minutes=max_age_minutes)


def _seed_paper_ideas_if_needed(session: Session) -> int:
    """Keep at least 3 tradeable ideas in stack for paper motor."""
    svc = TradeIdeaService(session)
    open_n = sum(
        1
        for i in svc.list_ideas(limit=80)
        if i.status in ("detected", "backtested", "confirmed")
    )
    if open_n >= 3:
        return 0

    from src.services.filipe_universe import CORE5_STOCKS

    seeds = [settings.golden_path_symbol] if settings.golden_path_mode else list(CORE5_STOCKS)
    created = 0
    for sym in seeds:
        if open_n + created >= 3:
            break
        try:
            svc.quick_seed_paper_idea(sym)
            created += 1
        except ValueError:
            continue
        except Exception:
            logger.exception("paper_seed_idea_failed", symbol=sym)
    if created:
        session.commit()
        logger.info("paper_ideas_seeded", count=created)
    return created


def run_orchestrator_cycle(session: Session) -> dict[str, Any]:
    """One motor tick: refresh scan/ideas, then autonomy confirm+execute."""
    global _last_run, _last_result
    settings = get_settings()
    errors: list[str] = []

    if not orchestrator_should_run():
        out = {"skipped": "orchestrator_inactive", "active": False}
        _last_result = {**out, "last_run": datetime.utcnow().isoformat()}
        return out

    if not motor_session_open():
        out = {"skipped": "outside_b3_window", "active": True}
        _last_result = {**out, "last_run": datetime.utcnow().isoformat()}
        return out

    summary = build_risk_summary(session)
    if summary.get("status") == "blocked":
        out = {"skipped": "risk_blocked", "active": True, "errors": ["daily loss limit"]}
        _last_result = {**out, "last_run": datetime.utcnow().isoformat()}
        return out

    scan_ran = False
    ideas_n = 0
    autonomy_out: dict = {"actions": [], "errors": []}

    if settings.paper_trading_mode and settings.paper_motor_auto_seed_ideas:
        try:
            ideas_n += _seed_paper_ideas_if_needed(session)
        except Exception as exc:
            errors.append(f"seed: {exc}")

    paper_motor = settings.paper_trading_mode and settings.auto_trading_on_sleeves
    if not paper_motor:
        try:
            if _scan_is_stale(session):
                PatternScanner(session).run_daily_scan()
                scan_ran = True
            ideas = TradeIdeaService(session).generate_from_latest_scan(limit=12)
            ideas_n += len(ideas)
        except Exception as exc:
            logger.exception("orchestrator_scan_failed")
            errors.append(f"scan: {exc}")

    try:
        autonomy_out = run_autonomy_cycle(session)
    except Exception as exc:
        logger.exception("orchestrator_autonomy_failed")
        errors.append(f"autonomy: {exc}")
        autonomy_out = {"actions": [], "errors": [str(exc)]}

    _last_run = datetime.utcnow()
    out = {
        "active": True,
        "scan_ran": scan_ran,
        "ideas_generated": ideas_n,
        "autonomy": autonomy_out,
        "errors": errors + list(autonomy_out.get("errors") or []),
    }
    _last_result = {**out, "last_run": _last_run.isoformat()}
    logger.info(
        "orchestrator_cycle",
        scan=scan_ran,
        ideas=ideas_n,
        actions=len(autonomy_out.get("actions") or []),
    )
    return out
