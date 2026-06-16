"""Persisted risk profile — singleton row per env (4.0-alpha)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.config import get_settings
from src.models import RiskProfile

DEFAULT_SECTOR_CAPS = {"default": 40.0}


def _defaults() -> dict:
    settings = get_settings()
    return {
        "max_daily_loss_brl": settings.default_daily_loss_limit_brl,
        "max_open_positions": settings.default_max_open_positions,
        "cost_per_trade_brl": 50.0,
        "max_net_delta": settings.max_portfolio_net_delta,
        "sector_caps": dict(DEFAULT_SECTOR_CAPS),
    }


def get_or_create_profile(session: Session) -> RiskProfile:
    profile = session.query(RiskProfile).order_by(RiskProfile.id).first()
    if profile:
        return profile
    defaults = _defaults()
    profile = RiskProfile(**defaults)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def profile_to_dict(profile: RiskProfile) -> dict:
    return {
        "max_daily_loss_brl": profile.max_daily_loss_brl,
        "max_open_positions": profile.max_open_positions,
        "cost_per_trade_brl": profile.cost_per_trade_brl,
        "max_net_delta": profile.max_net_delta,
        "sector_caps": profile.sector_caps or dict(DEFAULT_SECTOR_CAPS),
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


def update_profile(session: Session, payload: dict) -> RiskProfile:
    profile = get_or_create_profile(session)
    for key in (
        "max_daily_loss_brl",
        "max_open_positions",
        "cost_per_trade_brl",
        "max_net_delta",
        "sector_caps",
    ):
        if key in payload and payload[key] is not None:
            setattr(profile, key, payload[key])
    session.commit()
    session.refresh(profile)
    return profile
