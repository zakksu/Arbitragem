"""Trader Desk — risk budget + blotter + motor log (Phase A/B)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.services.motor_journal import list_recent
from src.services.risk_cockpit import build_risk_cockpit
from src.services.risk_profile import get_or_create_profile
from src.services.trading_desk import build_trading_desk
from src.services.trading_orchestrator import orchestrator_status
from src.services.trading_sleeves import status as sleeves_status


def build_risk_budget(session: Session, cockpit: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    profile = get_or_create_profile(session)
    max_loss = profile.max_daily_loss_brl
    day_pnl = float(cockpit.get("day_pnl") or 0)
    remaining_loss = round(max_loss + day_pnl, 2) if day_pnl < 0 else max_loss
    max_pos = profile.max_open_positions
    trades_today = int(cockpit.get("trades_today") or 0)
    return {
        "max_daily_loss_brl": max_loss,
        "day_pnl": day_pnl,
        "remaining_loss_budget_brl": remaining_loss,
        "max_open_positions": max_pos,
        "open_slots_used": trades_today,
        "paper_capital_brl": settings.paper_capital_brl,
        "net_delta": cockpit.get("net_delta"),
        "max_net_delta": cockpit.get("max_net_delta"),
        "gate_status": cockpit.get("gate_status"),
    }


def build_trader_desk(session: Session) -> dict[str, Any]:
    cockpit = build_risk_cockpit(session)
    desk = build_trading_desk(session)
    journal = list_recent(session, limit=get_settings().trader_desk_journal_limit)
    orchestrator = orchestrator_status()
    budget = build_risk_budget(session, cockpit)
    return {
        "cockpit": cockpit,
        "desk": desk,
        "journal": journal,
        "orchestrator": orchestrator,
        "budget": budget,
        "sleeves": sleeves_status(),
    }
