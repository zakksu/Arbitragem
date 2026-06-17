"""10.0 — Engine Mind + Visual Replay Player board partials."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.main import create_app
from src.models import init_db


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("BOARD_AUTH_ENABLED", "false")
    monkeypatch.setenv("BOARD_PASSWORD", "")
    init_db()
    return TestClient(create_app())


def test_engine_mind_partial(client: TestClient):
    r = client.get("/board/partials/engine-mind")
    assert r.status_code == 200
    assert "bb-engine-mind" in r.text
    assert "Engine Mind" in r.text
    assert "Sources" in r.text
    assert "Cycle breakdown" in r.text


def test_replay_player_partial(client: TestClient):
    r = client.get("/board/partials/replay-player", params={"symbol": "PETR4"})
    assert r.status_code == 200
    assert "bb-replay-player" in r.text
    assert "data-ticks=" in r.text
    assert "PETR4" in r.text


def test_symbol_panel_uses_replay_player(client: TestClient):
    r = client.get("/board/partials/symbol/PETR4")
    assert r.status_code == 200
    assert "replay-player" in r.text
    assert 'id="replay-player-slot"' in r.text


def test_build_engine_mind_shape():
    from src.web.engine_mind import build_engine_mind

    from src.models import get_session_factory, init_db

    init_db()
    session = get_session_factory()()
    try:
        mind = build_engine_mind(session)
    finally:
        session.close()
    assert "thinking" in mind
    assert "sources" in mind
    assert len(mind["sources"]) <= 5
    assert "phase_breakdown" in mind
    assert "journal" in mind


def test_build_replay_ticks():
    from src.web.replay_player import build_replay_ticks

    ticks = build_replay_ticks("PETR4", limit=40)
    assert len(ticks) >= 3
    assert "price" in ticks[0]
    assert "position" in ticks[0]
