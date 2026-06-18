"""Supervisor backlog — archaeology replay, futures quotes, Clear sync (11.0 GA prep)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import Trade, init_db


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'sup.db'}")
    monkeypatch.setenv("BOARD_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    init_db()
    return TestClient(create_app())


def test_futures_quotes_api(client: TestClient):
    r = client.get("/api/v1/quotes/futures")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 2
    assert body["session"]["session_status"] in ("open", "closed", "pre")
    syms = {q["symbol"] for q in body["quotes"]}
    assert "WINFUT" in syms or "WDOFUT" in syms


def test_replay_archaeology_batch(client: TestClient):
    from src.models import get_session_factory

    session = get_session_factory()()
    session.add(
        Trade(
            external_id="arch-r1",
            source="archaeology",
            symbol="VALE3",
            side="buy",
            quantity=100,
            price=62.0,
            executed_at=__import__("datetime").datetime(2025, 6, 1, 15, 0),
        )
    )
    session.commit()
    session.close()

    r = client.post("/api/v1/replay/archaeology/batch", json={"limit": 3, "auto_promote": False})
    assert r.status_code == 200
    body = r.json()
    assert "VALE3" in body.get("symbols", [])
    assert body.get("runs", 0) >= 1


def test_journal_sync_clear(client: TestClient):
    r = client.post("/api/v1/journal/sync/clear")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert "imported_clear" in body


def test_top_archaeology_symbols(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'arch.db'}")
    get_settings.cache_clear()
    init_db()
    from src.models import get_session_factory
    from src.services.archaeology_replay import top_archaeology_symbols

    session = get_session_factory()()
    for i in range(3):
        session.add(
            Trade(
                external_id=f"arch-{i}",
                source="archaeology",
                symbol="PETR4",
                side="buy",
                quantity=100,
                price=38.0,
                executed_at=__import__("datetime").datetime(2025, 1, i + 1),
            )
        )
    session.commit()
    syms = top_archaeology_symbols(session, limit=5)
    session.close()
    assert "PETR4" in syms
