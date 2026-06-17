"""Risk guardian — gates autonomous actions on sleeves + loss limits."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.services.risk_cockpit import build_risk_cockpit
from src.services.risk_summary import build_risk_summary
from src.services.trading_sleeves import SLEEVES, is_open


class RiskGuardian:
    """Pre-flight checks before scan, optimize, or execute."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def snapshot(self) -> dict[str, Any]:
        summary = build_risk_summary(self.session)
        cockpit = build_risk_cockpit(self.session)
        return {
            "summary": summary,
            "cockpit": cockpit,
            "sleeves_open": {s: is_open(s) for s in SLEEVES},
        }

    def can_run_autonomous(self) -> tuple[bool, str | None]:
        settings = get_settings()
        snap = self.snapshot()
        summary = snap["summary"]
        cockpit = snap["cockpit"]

        if summary.get("status") == "blocked":
            return False, "daily_loss_limit"

        if not settings.paper_trading_mode and cockpit.get("gate_status") == "blocked":
            return False, "portfolio_gate"

        if not any(is_open(s) for s in SLEEVES):
            return False, "all_sleeves_paused"

        return True, None
