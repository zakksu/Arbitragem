"""Autonomy engine — auto confirm/execute top ideas per open sleeve."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.logging_config import get_logger
from src.models import TradeIdea
from src.services.idea_score import score_idea
from src.services.risk_cockpit import build_risk_cockpit
from src.services.risk_summary import build_risk_summary
from src.services.trade_ideas import TradeIdeaService
from src.services.trading_sleeves import SLEEVES, is_open, sleeve_for_idea, status as sleeves_status

logger = get_logger(__name__)

_last_run: datetime | None = None
_last_result: dict[str, Any] = {
    "enabled": False,
    "last_run": None,
    "actions": [],
    "errors": [],
}


def autonomy_status() -> dict[str, Any]:
    from src.services.trading_orchestrator import b3_session_open

    settings = get_settings()
    return {
        "enabled": settings.autonomy_enabled,
        "max_trades_per_day": settings.autonomy_max_trades_per_day,
        "sleeves": sleeves_status(),
        "last_run": _last_result.get("last_run"),
        "last_actions": _last_result.get("actions", []),
        "last_errors": _last_result.get("errors", []),
        "b3_session_open": b3_session_open(),
    }


def _trades_today_count(session: Session) -> int:
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    return (
        session.query(TradeIdea)
        .filter(
            TradeIdea.status == "executed",
            TradeIdea.executed_at >= today_start,
        )
        .count()
    )


def run_autonomy_cycle(session: Session) -> dict[str, Any]:
    """
    Pick top confirmed-or-detected idea per open sleeve (max 1/sleeve, max 3 total).
    Auto-confirm if backtest gate or paper_override; auto-execute in paper or clear live.
    """
    global _last_run, _last_result
    settings = get_settings()
    actions: list[dict[str, Any]] = []
    errors: list[str] = []

    paper_auto = (
        settings.paper_trading_mode
        and settings.auto_trading_on_sleeves
        and any(is_open(x) for x in SLEEVES)
    )
    if not settings.autonomy_enabled and not paper_auto:
        out = {"skipped": "autonomy_disabled", "actions": [], "errors": []}
        _last_result = {**out, "enabled": False, "last_run": datetime.utcnow().isoformat()}
        return out

    summary = build_risk_summary(session)
    if settings.paper_trading_mode and settings.auto_trading_on_sleeves:
        if summary["status"] == "blocked":
            out = {"skipped": "risk_gate_blocked", "actions": [], "errors": ["daily loss limit"]}
            _last_result = {**out, "enabled": True, "last_run": datetime.utcnow().isoformat()}
            return out
    else:
        cockpit = build_risk_cockpit(session)
        if summary["status"] == "blocked" or cockpit["gate_status"] == "blocked":
            out = {"skipped": "risk_gate_blocked", "actions": [], "errors": ["risk gate blocked"]}
            _last_result = {**out, "enabled": True, "last_run": datetime.utcnow().isoformat()}
            return out

    if not any(is_open(s) for s in SLEEVES):
        out = {"skipped": "all_sleeves_paused", "actions": [], "errors": []}
        _last_result = {**out, "enabled": True, "last_run": datetime.utcnow().isoformat()}
        return out

    svc = TradeIdeaService(session)
    ideas = [svc.to_dict(i) for i in svc.list_ideas(limit=80)]
    open_stack = [i for i in ideas if i.get("status") not in ("rejected", "executed")]

    trades_today = _trades_today_count(session)
    cap = settings.autonomy_max_trades_per_day
    if cap > 0:
        budget = max(0, cap - trades_today)
        if budget <= 0:
            out = {"skipped": "daily_trade_cap", "actions": [], "errors": []}
            _last_result = {**out, "enabled": True, "last_run": datetime.utcnow().isoformat()}
            return out
    else:
        budget = 9999

    by_sleeve: dict[str, dict[str, Any]] = {}
    for idea in open_stack:
        if idea.get("status") not in ("detected", "backtested", "confirmed"):
            continue
        sleeve = sleeve_for_idea(idea)
        if not is_open(sleeve):
            continue
        sc = score_idea(idea, open_stack=open_stack)
        idea = {**idea, "idea_score": sc}
        prev = by_sleeve.get(sleeve)
        if prev is None or sc > prev.get("idea_score", 0):
            by_sleeve[sleeve] = idea

    ranked = sorted(by_sleeve.values(), key=lambda x: x.get("idea_score", 0), reverse=True)
    max_pick = 1 if settings.paper_trading_mode and settings.auto_trading_on_sleeves else 3
    if settings.paper_trading_mode:
        ranked = [i for i in ranked if sleeve_for_idea(i) == "cash" or i.get("structure_type") == "scalp_long"]
    picked = ranked[: min(max_pick, budget)]

    for idea in picked:
        idea_id = idea["id"]
        sleeve = sleeve_for_idea(idea)
        try:
            if idea["status"] in ("detected", "backtested"):
                paper_ov = settings.paper_trading_mode
                gate_ok = svc.passes_backtest_gate(idea.get("backtest_proof"))
                if not gate_ok and not paper_ov:
                    errors.append(f"#{idea_id} backtest gate failed")
                    continue
                svc.confirm_idea(idea_id, paper_override=paper_ov or not gate_ok)
                actions.append(
                    {"action": "confirm", "idea_id": idea_id, "sleeve": sleeve, "symbol": idea.get("symbol")}
                )
                idea = svc.to_dict(session.get(TradeIdea, idea_id) or idea)

            if idea.get("status") == "confirmed":
                backend = (settings.execution_backend or "profit").lower()
                if backend == "profit" or settings.paper_trading_mode:
                    svc.execute_idea(idea_id)
                    mode = backend if backend == "profit" else "paper"
                    actions.append(
                        {
                            "action": "execute",
                            "idea_id": idea_id,
                            "mode": mode,
                            "symbol": idea.get("symbol"),
                            "sleeve": sleeve,
                        }
                    )
                elif backend == "clear":
                    from src.integrations.clear_api import get_clear_client

                    if get_clear_client().is_configured():
                        svc.execute_idea(idea_id)
                        actions.append({"action": "execute", "idea_id": idea_id, "mode": "clear"})
                    else:
                        errors.append(f"#{idea_id} clear not configured — use EXECUTION_BACKEND=profit")
                else:
                    svc.execute_idea(idea_id)
                    actions.append({"action": "execute", "idea_id": idea_id, "mode": backend})
        except ValueError as exc:
            errors.append(f"#{idea_id}: {exc}")
        except Exception as exc:
            logger.exception("autonomy_cycle_error", idea_id=idea_id)
            errors.append(f"#{idea_id}: {exc}")

    _last_run = datetime.utcnow()
    out = {"actions": actions, "errors": errors, "picked": len(picked)}
    _last_result = {
        **out,
        "enabled": True,
        "last_run": _last_run.isoformat(),
    }
    logger.info("autonomy_cycle", actions=len(actions), errors=len(errors))
    return out
