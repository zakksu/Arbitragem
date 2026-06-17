"""Idea lifecycle gate evaluation — A2.10."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.models import TradeIdea
from src.services.risk_summary import build_risk_summary
from src.services.trade_ideas import TradeIdeaService
from src.services.trading_sleeves import ensure_sleeve_open, sleeve_for_idea


def build_idea_gates(session: Session, idea_id: int) -> dict[str, Any]:
    idea = session.get(TradeIdea, idea_id)
    if not idea:
        raise ValueError("Idea not found")

    svc = TradeIdeaService(session)
    idea_dict = svc.to_dict(idea)
    settings = get_settings()
    blockers: list[str] = []

    backtest_pass = svc.passes_backtest_gate(idea.backtest_proof)
    if not backtest_pass and not settings.paper_trading_mode:
        blockers.append("backtest_gate_failed")

    risk = build_risk_summary(session)
    sleeve = sleeve_for_idea(idea_dict)
    sleeve_open = True
    try:
        ensure_sleeve_open(sleeve, "confirm")
    except ValueError as exc:
        sleeve_open = False
        blockers.append(str(exc))

    if not risk.get("can_execute_ideas"):
        blockers.append("risk_gate_blocked")

    from src.services.risk_cockpit import confirm_blocked_by_portfolio

    portfolio_block = confirm_blocked_by_portfolio(session, idea.legs)
    if portfolio_block:
        blockers.append(portfolio_block)

    status = idea.status
    can_confirm = status in ("detected", "backtested") and sleeve_open and not portfolio_block
    if not backtest_pass and not settings.paper_trading_mode:
        can_confirm = False
    can_execute = (
        status == "confirmed"
        and sleeve_open
        and risk.get("can_execute_ideas")
        and not portfolio_block
    )

    return {
        "idea_id": idea_id,
        "status": status,
        "sleeve": sleeve,
        "backtest_gate_pass": backtest_pass,
        "paper_override_available": settings.paper_trading_mode,
        "can_confirm": can_confirm,
        "can_execute": can_execute,
        "blockers": blockers,
        "lifecycle": ["detected", "backtested", "confirmed", "executed", "reviewed"],
        "next_states": _next_states(status),
    }


def _next_states(status: str) -> list[str]:
    mapping = {
        "detected": ["backtested", "confirmed", "rejected"],
        "backtested": ["confirmed", "rejected"],
        "confirmed": ["executed", "rejected"],
        "executed": ["reviewed"],
    }
    return mapping.get(status, [])
