"""Release 13.0 GA — Core5, replay batch, journal desk, Phase C."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import init_db
from src.services.filipe_universe import core5_symbol_list, load_filipe_core5
from src.services.replay_batch import replay_universe, strategies_for_symbol
from src.services.self_healing.health_registry import _probe_api


@pytest.fixture
def client(monkeypatch, tmp_path):
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 't13.db'}")
    monkeypatch.setenv("SCANNER_MODE", "filipe_core5")
    monkeypatch.setenv("AUTONOMY_MAX_TRADES_PER_DAY", "0")
    init_db()
    return TestClient(create_app())


def test_version_13():
    from src import __version__

    assert __version__ == "14.0.0-alpha"


def test_core5_universe():
    rows = load_filipe_core5()
    assert len(rows) == 5
    assert core5_symbol_list() == ["PETR4", "VALE3", "ITUB4", "BOVA11", "PRIO3"]


def test_scanner_mode_core5(monkeypatch):
    monkeypatch.setenv("SCANNER_MODE", "filipe_core5")
    get_settings.cache_clear()
    syms = get_settings().scanner_symbol_list
    assert "PETR4" in syms
    assert "BBAS3" not in syms


def test_replay_universe_includes_win():
    uni = replay_universe()
    assert "WINFUT" in uni
    assert "PETR4" in uni
    assert len(strategies_for_symbol("WINFUT")) == 5
    assert len(strategies_for_symbol("PETR4")) == 5


def test_health_probe_in_process():
    assert _probe_api() is True


def test_journal_desk_api(client: TestClient):
    r = client.get("/api/v1/journal/desk")
    assert r.status_code == 200
    assert "summary" in r.json()


def test_journal_csv_export(client: TestClient):
    r = client.get("/api/v1/journal/export.csv")
    assert r.status_code == 200
    assert "symbol" in r.text


def test_phase_c_status(client: TestClient):
    r = client.get("/api/v1/phase-c/status")
    assert r.status_code == 200
    body = r.json()
    assert "passed" in body
    assert "criteria" in body


def test_trade_journal_partial(client: TestClient):
    r = client.get("/board/partials/trade-journal")
    assert r.status_code == 200
    assert "Trade Journal" in r.text


def test_replay_batch_endpoint(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        "src.services.replay_engine.start_replay",
        lambda **kw: {"status": "completed", "job_id": "x", "fill_count": 1},
    )
    r = client.post("/api/v1/replay/batch", json={"auto_promote": False})
    assert r.status_code == 200
    assert r.json()["runs"] >= 1


def test_live_radar_phase_c_blocker(client: TestClient):
    r = client.get("/api/v1/ops/live-radar")
    body = r.json()
    assert "ready_to_execute" in body
    assert "phase_c" in body
