"""Release 11.0-beta — Strategy Lab strip, NTSL match, structure replay."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import StoredStrategy, init_db


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 't11.db'}")
    monkeypatch.setenv("BOARD_AUTH_ENABLED", "false")
    get_settings.cache_clear()
    init_db()
    return TestClient(create_app())


def test_strategy_lab_strip_partial(client: TestClient):
    r = client.get("/board/partials/strategy-lab-strip")
    assert r.status_code == 200
    assert "bb-sl-structure-chip" in r.text
    assert "strategy-lab-rankings" in r.text


def test_rankings_table_desk_target(client: TestClient):
    r = client.get("/board/partials/rankings-table?detail_target=strategy-lab-detail-slot")
    assert r.status_code == 200
    assert "data-detail-target=\"strategy-lab-detail-slot\"" in r.text


def test_match_ntsl_for_structure(db_session):
    from src.services.strategy_store import match_ntsl_for_structure

    db_session.add(
        StoredStrategy(
            name="s1_vwap_reclaim_PETR4",
            file_path="/tmp/test.ntsl",
            content_hash="abc",
            tags=["vwap", "scalp", "s1"],
            symbols=["PETR4"],
            last_scanned_at=datetime.utcnow(),
        )
    )
    db_session.commit()
    match = match_ntsl_for_structure(db_session, "stock_scalp_vwap", symbol="PETR4")
    assert match is not None
    assert match["match_score"] > 0
    assert match["replay_strategy"] == "s1_vwap_reclaim"


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 't11b.db'}")
    get_settings.cache_clear()
    init_db()
    from src.models import get_session_factory

    session = get_session_factory()()
    yield session
    session.close()
