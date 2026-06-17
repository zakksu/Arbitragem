"""10.0 GA — board partials for brief, learning, graduation."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.main import create_app
from src.models import Trade, TradeIdea, init_db


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ui10.db'}")
    monkeypatch.setenv("KNOWLEDGE_DB_PATH", str(tmp_path / "knowledge.db"))
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("BOARD_AUTH_ENABLED", "false")
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    init_db()
    return TestClient(create_app())


def test_learning_rail_partial(client: TestClient):
    r = client.get("/board/partials/learning-rail")
    assert r.status_code == 200
    assert "bb-learning-rail" in r.text


def test_decision_queue_partial(client: TestClient):
    r = client.get("/board/partials/decision-queue")
    assert r.status_code == 200
    assert "bb-decision-queue" in r.text


def test_confirm_step_includes_brief(client: TestClient):
    from src.models import get_session_factory

    session = get_session_factory()()
    idea = TradeIdea(symbol="PETR4", structure_type="scalp_long", side="long", status="detected")
    session.add(idea)
    session.commit()
    iid = idea.id
    session.close()

    r = client.get(f"/board/partials/ideas/{iid}/confirm-step")
    assert r.status_code == 200
    assert "bb-decision-brief" in r.text or "Decision brief" in r.text


def test_watchlist_graduation_badge(client: TestClient):
    from src.models import get_session_factory

    session = get_session_factory()()
    for i in range(6):
        session.add(
            Trade(
                external_id=f"g-{i}",
                source="paper",
                symbol="PETR4",
                side="buy",
                quantity=100,
                price=38.0,
                pnl=1.0,
                executed_at=__import__("datetime").datetime.utcnow(),
            )
        )
    session.commit()
    session.close()

    r = client.get("/board/partials/watchlist")
    assert r.status_code == 200
    assert "bb-grad" in r.text or "GRAD" in r.text
