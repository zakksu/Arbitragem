"""Portfolio risk cockpit — net delta, sector exposure, margin stub (3.0-beta)."""

from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.config import get_settings
from src.integrations.profit_bridge import get_profit_client
from src.models import Trade, TradeIdea
from src.services.filipe_universe import sector_for
from src.services.risk_summary import build_risk_summary
from src.services.risk_profile import get_or_create_profile


def _leg_delta(leg: dict) -> float:
    """Stub portfolio delta from leg type + greeks bridge."""
    sym = str(leg.get("symbol", "")).upper()
    qty = int(leg.get("quantity", 100))
    leg_type = str(leg.get("leg_type", "cash"))
    side_mult = 1.0 if leg.get("side") == "buy" else -1.0

    if leg_type == "cash":
        return round(side_mult * qty / 10_000.0, 4)

    client = get_profit_client()
    greeks = client.get_greeks(sym)
    delta = float(greeks.get("delta", 0.35))
    return round(side_mult * delta * qty / 100.0, 4)


def estimate_legs_delta(legs: list[dict] | None) -> float:
    if not legs:
        return 0.0
    return round(sum(_leg_delta(leg) for leg in legs), 4)


def _open_idea_legs(session: Session) -> list[dict]:
    """Legs from confirmed or executed structures only (not pending stack)."""
    legs: list[dict] = []
    ideas = (
        session.query(TradeIdea)
        .filter(TradeIdea.status.in_(["confirmed", "executed"]))
        .all()
    )
    for idea in ideas:
        if idea.status == "executed" and idea.executed_at:
            if idea.executed_at.date() < datetime.utcnow().date():
                continue
        legs.extend(idea.legs or [])
    return legs


def _sector_exposure(session: Session) -> dict[str, float]:
    """Notional % by sector from today's trades + open idea legs."""
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    trades = session.query(Trade).filter(Trade.executed_at >= today_start).all()
    notional_by_sector: dict[str, float] = {}
    total = 0.0
    for t in trades:
        sector = sector_for(t.symbol) or "other"
        n = abs(t.quantity * t.price)
        notional_by_sector[sector] = notional_by_sector.get(sector, 0.0) + n
        total += n
    if total <= 0:
        for leg in _open_idea_legs(session):
            sym = leg.get("symbol", "")
            sector = sector_for(sym) or "other"
            n = abs(int(leg.get("quantity", 100)) * 10.0)
            notional_by_sector[sector] = notional_by_sector.get(sector, 0.0) + n
            total += n
    if total <= 0:
        return {}
    return {k: round(v / total * 100.0, 1) for k, v in notional_by_sector.items()}


def _margin_estimate_stub(legs: list[dict], entry_price: float = 0.0) -> float:
    margin = 0.0
    for leg in legs:
        qty = int(leg.get("quantity", 100))
        leg_type = str(leg.get("leg_type", "cash"))
        if leg_type == "cash":
            margin += qty * (entry_price or 10.0) * 0.2
        else:
            margin += qty * 2.5
    return round(margin, 2)


def build_risk_cockpit(session: Session) -> dict:
    settings = get_settings()
    profile = get_or_create_profile(session)
    summary = build_risk_summary(session)
    legs = _open_idea_legs(session)
    net_delta = estimate_legs_delta(legs)
    sector_pct = _sector_exposure(session)
    top_sector = max(sector_pct, key=sector_pct.get) if sector_pct else None
    margin_est = _margin_estimate_stub(legs)
    max_net_delta = profile.max_net_delta

    gate_status = summary["status"]
    if gate_status != "blocked" and abs(net_delta) > max_net_delta:
        gate_status = "blocked"

    sector_cap = (profile.sector_caps or {}).get("default", 40.0)
    if top_sector and sector_pct.get(top_sector, 0.0) > sector_cap:
        if gate_status == "ok":
            gate_status = "warning"

    return {
        "paper_trading_mode": settings.paper_trading_mode,
        "day_pnl": summary["day_pnl"],
        "pnl_source": summary["pnl_source"],
        "profit_day_pnl": summary.get("profit_day_pnl"),
        "net_delta": net_delta,
        "max_net_delta": max_net_delta,
        "net_delta_used_pct": round(
            min(100.0, abs(net_delta) / max(max_net_delta, 0.01) * 100), 1
        ),
        "sector_exposure_pct": sector_pct,
        "top_sector": top_sector,
        "top_sector_pct": sector_pct.get(top_sector, 0.0) if top_sector else 0.0,
        "margin_estimate_brl": margin_est,
        "gate_status": gate_status,
        "loss_gate_status": summary["status"],
        "can_confirm": gate_status == "ok",
        "trades_today": summary["trades_today"],
    }


def confirm_blocked_by_portfolio(session: Session, new_legs: list[dict] | None) -> str | None:
    """Return error message if confirm would breach portfolio net delta."""
    profile = get_or_create_profile(session)
    cockpit = build_risk_cockpit(session)
    if cockpit["loss_gate_status"] == "blocked":
        return "Daily loss limit blocked — cannot confirm"
    added = estimate_legs_delta(new_legs)
    projected = round(cockpit["net_delta"] + added, 4)
    limit = profile.max_net_delta
    if abs(projected) > limit:
        return (
            f"Portfolio net delta {projected:+.2f} exceeds limit "
            f"±{limit}"
        )
    return None
