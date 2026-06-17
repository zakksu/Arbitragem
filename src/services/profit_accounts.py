"""ProfitChart / Clear account profiles — Sim vs Day vs Swing."""

from __future__ import annotations

from typing import Any

from src.config import Settings, get_settings


def resolve_profit_account(settings: Settings | None = None) -> dict[str, Any]:
    """
    Map app mode to the ProfitChart account Filipe should have selected.

    Paper (PAPER_TRADING_MODE=true) → Simulador 3368.
    Live → Clear DayTrade or SwingTrade (same broker id, different Profit routing).
  """
    s = settings or get_settings()
    if s.paper_trading_mode:
        return {
            "profile": "sim",
            "label": "Clear Paper (Sim)",
            "broker": "profit_sim",
            "account_id": s.profit_account_sim_id,
            "holder": s.profit_account_sim_name,
            "display": f"Paper Sim {s.profit_account_sim_id} — R$ {s.paper_capital_brl:,.0f}",
            "is_paper": True,
            "clear_account_id": None,
        }

    style = (s.profit_live_style or "day").lower()
    if style == "swing":
        return {
            "profile": "swing",
            "label": "Clear - SwingTrade",
            "broker": "clear",
            "account_id": s.profit_account_swing_id,
            "holder": s.profit_account_live_name,
            "display": f"Clear Swing {s.profit_account_swing_id} — {s.profit_account_live_name}",
            "is_paper": False,
            "clear_account_id": s.clear_account_id or s.profit_account_swing_id,
        }

    return {
        "profile": "day",
        "label": "Clear - DayTrade",
        "broker": "clear",
        "account_id": s.profit_account_day_id,
        "holder": s.profit_account_live_name,
        "display": f"Clear Day {s.profit_account_day_id} — {s.profit_account_live_name}",
        "is_paper": False,
        "clear_account_id": s.clear_account_id or s.profit_account_day_id,
    }


def profit_account_checklist(settings: Settings | None = None) -> list[dict[str, Any]]:
    """Setup wizard rows for the three Profit accounts."""
    s = settings or get_settings()
    active = resolve_profit_account(s)
    rows = [
        {
            "id": "sim",
            "label": "Simulador (paper)",
            "account_id": s.profit_account_sim_id,
            "holder": s.profit_account_sim_name,
            "active": active["profile"] == "sim",
        },
        {
            "id": "day",
            "label": "Clear - DayTrade",
            "account_id": s.profit_account_day_id,
            "holder": s.profit_account_live_name,
            "active": active["profile"] == "day",
        },
        {
            "id": "swing",
            "label": "Clear - SwingTrade",
            "account_id": s.profit_account_swing_id,
            "holder": s.profit_account_live_name,
            "active": active["profile"] == "swing",
        },
    ]
    return rows
