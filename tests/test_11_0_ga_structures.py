"""11.0 GA — F1-F5 futures structures, sizer API, scanner roll."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import init_db
from src.services.futures_roll import resolve_futures_quote_symbol
from src.services.structure_types import FUTURES_MOTOR_STRUCTURES, replay_strategy_for_structure


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ga11.db'}")
    get_settings.cache_clear()
    init_db()
    return TestClient(create_app())


def test_futures_structures_map_to_replay():
    assert len(FUTURES_MOTOR_STRUCTURES) == 5
    assert replay_strategy_for_structure("futures_open_drive") == "f1_open_drive"
    assert replay_strategy_for_structure("futures_failed_breakout") == "f5_failed_breakout"


def test_win_front_month_resolver():
    meta = resolve_futures_quote_symbol("WINFUT")
    assert meta["requested"] == "WINFUT"
    assert meta["resolved"].startswith("WIN")
    assert len(meta["resolved"]) >= 5


def test_futures_sizer_api(client: TestClient):
    r = client.get("/api/v1/futures/sizer/WINFUT?capital=1500")
    assert r.status_code == 200
    body = r.json()
    assert body["is_futures"] is True
    assert body["max_contracts"] == 1
