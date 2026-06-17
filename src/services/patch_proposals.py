"""Patch proposals — generate, approve, reject (10.0-rc)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.models import PatchProposal
from src.services.outcome_ranker import rank_outcomes
from src.services.theory_cards import build_theory_cards


def generate_patch_proposals(session: Session, *, symbol: str | None = None) -> list[dict[str, Any]]:
    """Create pending patches from weak outcome patterns."""
    created: list[dict[str, Any]] = []
    for row in rank_outcomes(session, symbol=symbol, limit=10):
        if row["win_rate_pct"] >= 45 and row["total_pnl"] >= 0:
            continue
        sym = row["symbol"]
        existing = (
            session.query(PatchProposal)
            .filter(PatchProposal.symbol == sym, PatchProposal.status == "pending")
            .first()
        )
        if existing:
            continue
        cards = build_theory_cards(symbol=sym, limit=2)
        prop = PatchProposal(
            symbol=sym,
            pattern=row.get("source"),
            status="pending",
            diff={
                "backtest_min_profit_factor": 1.4,
                "max_daily_loss_brl": 450,
            },
            evidence=row,
            theory_card_ids=[c.get("id") for c in cards],
        )
        session.add(prop)
        session.flush()
        created.append(proposal_to_dict(prop))
    session.commit()
    return created


def list_proposals(session: Session, *, status: str | None = "pending") -> list[dict[str, Any]]:
    q = session.query(PatchProposal).order_by(PatchProposal.created_at.desc())
    if status:
        q = q.filter(PatchProposal.status == status)
    return [proposal_to_dict(p) for p in q.limit(50).all()]


def approve_proposal(session: Session, proposal_id: int) -> dict[str, Any]:
    prop = session.get(PatchProposal, proposal_id)
    if not prop:
        raise ValueError("Proposal not found")
    if prop.status != "pending":
        raise ValueError(f"Proposal already {prop.status}")

    from src.services.symbol_factory import apply_patch_to_symbol

    apply_patch_to_symbol(prop.symbol, prop.diff or {})
    prop.status = "approved"
    prop.resolved_at = datetime.utcnow()
    session.commit()
    return proposal_to_dict(prop)


def reject_proposal(session: Session, proposal_id: int, *, reason: str = "") -> dict[str, Any]:
    prop = session.get(PatchProposal, proposal_id)
    if not prop:
        raise ValueError("Proposal not found")
    prop.status = "rejected"
    prop.resolved_at = datetime.utcnow()
    ev = dict(prop.evidence or {})
    ev["reject_reason"] = reason[:200]
    prop.evidence = ev
    session.commit()
    return proposal_to_dict(prop)


def proposal_to_dict(p: PatchProposal) -> dict[str, Any]:
    return {
        "id": p.id,
        "symbol": p.symbol,
        "pattern": p.pattern,
        "status": p.status,
        "diff": p.diff,
        "evidence": p.evidence,
        "theory_card_ids": p.theory_card_ids,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "resolved_at": p.resolved_at.isoformat() if p.resolved_at else None,
    }
