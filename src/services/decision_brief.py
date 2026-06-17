"""Decision brief — RAG context + Ollama, max 5 bullets (10.0-beta)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.models import TradeIdea
from src.services.conflict_detector import detect_conflicts
from src.services.theory_cards import build_theory_cards
from src.services.trade_ideas import TradeIdeaService


def build_decision_brief(session: Session, idea_id: int) -> dict[str, Any]:
    idea = session.get(TradeIdea, idea_id)
    if not idea:
        raise ValueError("Idea not found")

    meta = idea.meta or {}
    cards = meta.get("theory_cards") or build_theory_cards(
        symbol=idea.symbol,
        structure_type=idea.structure_type,
        tags=idea.rationale_tags,
    )
    if not meta.get("theory_cards"):
        idea.meta = {**meta, "theory_cards": cards, "theory_card_count": len(cards)}
        session.flush()

    context_parts = [
        f"Symbol: {idea.symbol} · {idea.structure_type} · {idea.side} · status={idea.status}",
        f"Rationale: {(idea.rationale or '')[:500]}",
    ]
    for c in cards[:3]:
        context_parts.append(f"[{c.get('title')}] {c.get('excerpt', '')[:240]}")

    bullets: list[str] = []
    summary = ""
    settings = get_settings()
    if settings.ollama_runtime_enabled:
        from src.integrations.ollama_client import get_ollama_client

        client = get_ollama_client()
        if client.is_available():
            raw = client.chat(
                "Give exactly 5 short bullets: action (take/skip/wait), entry, stop, target, risk. "
                "Use only the context provided.",
                context="\n".join(context_parts),
            )
            summary = raw
            bullets = [ln.strip().lstrip("-•* ") for ln in raw.splitlines() if ln.strip()][:5]

    if not bullets:
        bullets = [
            f"{'Paper' if settings.paper_trading_mode else 'Live'} mode — verify gates before confirm.",
            f"Structure: {idea.structure_type} {idea.side} on {idea.symbol}.",
            f"Theory sources: {len(cards)} card(s)" if cards else "No corpus match — rules-only decision.",
            "Stop/target: use Trade Product levels.",
            "Skip if sleeve or risk gate blocked.",
        ]
        summary = "Rule-based brief (Ollama offline)."

    conflicts = detect_conflicts(session, idea_id, bullets=bullets)
    idea.meta = {
        **meta,
        "decision_brief": {"bullets": bullets, "conflicts": conflicts},
    }
    session.flush()
    return {
        "idea_id": idea_id,
        "symbol": idea.symbol,
        "bullets": bullets,
        "summary": summary,
        "theory_cards": cards,
        "theory_card_count": len(cards),
        "no_corpus_match": len(cards) == 0,
        "conflicts": conflicts,
        "can_confirm": not any(c.get("severity") == "hard" for c in conflicts),
    }
