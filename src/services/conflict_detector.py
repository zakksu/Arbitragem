"""Conflict detector — brief vs gates and backtest (10.0-beta)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.models import TradeIdea
from src.services.idea_gates import build_idea_gates


def detect_conflicts(
    session: Session,
    idea_id: int,
    *,
    bullets: list[str] | None = None,
) -> list[dict[str, Any]]:
    idea = session.get(TradeIdea, idea_id)
    if not idea:
        return [{"code": "idea_missing", "severity": "hard", "message": "Idea not found"}]

    gates = build_idea_gates(session, idea_id)
    conflicts: list[dict[str, Any]] = []
    text = " ".join(bullets or []).lower()

    if not gates.get("backtest_gate_pass") and "take" in text and "skip" not in text:
        conflicts.append(
            {
                "code": "backtest_mismatch",
                "severity": "hard",
                "message": "Brief suggests take but backtest gate failed",
            }
        )

    if gates.get("blockers"):
        conflicts.append(
            {
                "code": "gate_blockers",
                "severity": "hard",
                "message": "; ".join(gates["blockers"][:3]),
            }
        )

    loser_phrases = ("add to loser", "average down", "double down")
    if any(p in text for p in loser_phrases):
        conflicts.append(
            {
                "code": "risk_language",
                "severity": "hard",
                "message": "Brief contains prohibited averaging-down language",
            }
        )

    proof = idea.backtest_proof or {}
    if proof.get("max_drawdown_pct") and float(proof["max_drawdown_pct"]) > 8 and "aggressive" in text:
        conflicts.append(
            {
                "code": "drawdown_tone",
                "severity": "soft",
                "message": "High drawdown in proof but brief sounds aggressive",
            }
        )

    return conflicts
