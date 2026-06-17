"""Offline rule distillation from knowledge corpus (10.0-beta)."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from typing import Any

from src.services.knowledge.store import _connect, init_knowledge_db


def distill_candidate_axioms(*, limit: int = 20) -> dict[str, Any]:
    """Cluster frequent tags into candidate axioms — no auto-apply."""
    init_knowledge_db()
    tags: Counter[str] = Counter()
    with _connect() as conn:
        rows = conn.execute("SELECT tags FROM knowledge_chunks LIMIT 5000").fetchall()
    for row in rows:
        try:
            for t in json.loads(row[0] or "[]"):
                tags[str(t).lower()] += 1
        except (json.JSONDecodeError, TypeError):
            continue

    axioms = [
        {"tag": tag, "weight": count, "axiom": f"Prefer setups tagged '{tag}' when PF gate passes"}
        for tag, count in tags.most_common(limit)
        if count >= 2
    ]
    return {"axioms": axioms, "count": len(axioms)}
