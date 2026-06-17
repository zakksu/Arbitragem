"""10.0 — Engine Mind, Replay Player, Companion, Strategy Store, Briefing UI."""

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
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    init_db()
    return TestClient(create_app())


def test_engine_mind_partial(client: TestClient):
    r = client.get("/board/partials/engine-mind")
    assert r.status_code == 200
    assert "bb-engine-mind" in r.text
    assert "Sources" in r.text
    assert "resources" not in r.text.lower() or "replay_workers" in r.text or "MB" in r.text


def test_replay_player_partial(client: TestClient):
    r = client.get("/board/partials/replay-player", params={"symbol": "PETR4"})
    assert r.status_code == 200
    assert "bb-replay-player" in r.text
    assert "Run replay" in r.text
    assert "data-ticks=" in r.text


def test_replay_player_run(client: TestClient):
    r = client.post(
        "/board/partials/replay-player/run",
        data={"symbol": "PETR4", "strategy": "scalp_default", "speed": "8"},
    )
    assert r.status_code == 200
    assert "bb-replay-player" in r.text
    assert "job" in r.text.lower() or "fills" in r.text.lower()


def test_profitchart_companion_partial(client: TestClient):
    r = client.get("/board/partials/profitchart-companion", params={"symbol": "PETR4"})
    assert r.status_code == 200
    assert "bb-pc-companion" in r.text
    assert "ProfitChart Companion" in r.text


def test_strategy_store_partial(client: TestClient):
    r = client.get("/board/partials/strategy-store")
    assert r.status_code == 200
    assert "bb-strategy-store" in r.text
    assert "Scan NTSL" in r.text


def test_strategy_store_scan(client: TestClient):
    r = client.post("/board/partials/strategy-store/scan")
    assert r.status_code == 200
    assert "bb-strategy-store" in r.text


def test_daily_briefing_partial(client: TestClient):
    r = client.get("/board/partials/daily-briefing")
    assert r.status_code == 200
    assert "bb-daily-briefing" in r.text
    assert "Daily briefing" in r.text


def test_symbol_panel_companion_and_replay(client: TestClient):
    r = client.get("/board/partials/symbol/PETR4")
    assert r.status_code == 200
    assert "profitchart-companion-slot" in r.text
    assert "replay-player-slot" in r.text


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
    assert "backend" in mind
    assert "resources" in mind


def test_build_replay_ticks():
    from src.web.replay_player import build_replay_ticks

    ticks = build_replay_ticks("PETR4", limit=40)
    assert len(ticks) >= 3
    assert "price" in ticks[0]


def test_build_profitchart_companion():
    from src.web.profitchart_companion import build_profitchart_companion

    ctx = build_profitchart_companion(
        "PETR4",
        quote={"last": 38.5},
        top_idea={"entry": 38.0, "stop": 37.5, "target": 39.0},
        session_vwap={"session_vwap": 38.2, "vwap_distance_pct": 0.5},
    )
    assert ctx["symbol"] == "PETR4"
    assert len(ctx["levels"]) >= 3
