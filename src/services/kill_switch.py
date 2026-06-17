"""Deprecated kill switch shim — delegates to trading sleeves (all off/on)."""

from __future__ import annotations

from src.services.trading_sleeves import set_all, status as sleeves_status


def is_active() -> bool:
    return not sleeves_status()["all_open"]


def status() -> dict:
    st = sleeves_status()
    active = not st["all_open"]
    return {
        "active": active,
        "activated_at": None,
        "reason": st.get("reason") if active else None,
        "sleeves": st["sleeves"],
    }


def set_active(active: bool, reason: str = "") -> dict:
    set_all(not active, reason=reason if active else "")
    return status()


def ensure_not_blocked(action: str = "confirm") -> None:
    from src.services.trading_sleeves import ensure_all_sleeves_open

    ensure_all_sleeves_open(action)
