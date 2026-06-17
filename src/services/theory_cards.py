"""Theory cards — link knowledge chunks to trade ideas (10.0-beta)."""

from __future__ import annotations

from typing import Any

from src.services.knowledge.store import search_chunks


def build_theory_cards(
    *,
    symbol: str,
    structure_type: str | None = None,
    tags: list[str] | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Retrieve top knowledge chunks as theory cards."""
    sym = symbol.strip().upper()
    queries = [sym]
    if structure_type:
        queries.append(structure_type.replace("_", " "))
    if tags:
        queries.extend(tags[:2])

    seen: set[int] = set()
    cards: list[dict[str, Any]] = []
    for q in queries:
        for hit in search_chunks(q, symbol=sym, limit=limit):
            cid = hit.get("id")
            if cid in seen:
                continue
            seen.add(cid)
            cards.append(
                {
                    "id": f"tc-{cid}",
                    "chunk_id": cid,
                    "title": hit.get("title") or "Theory",
                    "source_uri": hit.get("source_uri"),
                    "excerpt": hit.get("excerpt"),
                    "tags": hit.get("tags") or [],
                    "symbols": hit.get("symbols") or [sym],
                }
            )
            if len(cards) >= limit:
                return cards
    return cards


def attach_cards_to_idea_meta(meta: dict | None, cards: list[dict[str, Any]]) -> dict[str, Any]:
    out = dict(meta or {})
    out["theory_cards"] = cards
    out["theory_card_count"] = len(cards)
    return out
