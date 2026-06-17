"""Trust scorecard composite gates (Release 7.0)."""

from __future__ import annotations

import pytest

from src.models import get_session_factory, init_db
from src.services.trust_scorecard import build_trust_scorecard


def test_trust_scorecard_structure(monkeypatch):
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    init_db()
    session = get_session_factory()()
    try:
        items = [{"ok": True}, {"ok": False}]
        data = build_trust_scorecard(session, checklist_items=items)
        assert "score_pct" in data
        assert "passing" in data
        assert "components" in data
        assert data["components"]["checklist"]["ok"] == 1
    finally:
        session.close()
