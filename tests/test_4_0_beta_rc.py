"""4.0-beta/rc API smoke tests."""

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import init_db


@pytest.fixture
def client(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    init_db()
    return TestClient(create_app())


def test_pulse_rail_api(client):
    r = client.get("/api/v1/pulse")
    assert r.status_code == 200
    data = r.json()
    assert "news" in data and "calendar" in data and "lesson" in data


def test_pulse_rail_partial(client):
    r = client.get("/board/partials/pulse-rail")
    assert r.status_code == 200
    assert "bb-pulse-rail" in r.text


def test_replay_run_sandbox(client):
    r = client.post(
        "/api/v1/replay/run",
        json={"strategy": "scalp_default", "symbol": "PETR4", "speed": 10, "mode": "sandbox"},
    )
    assert r.status_code == 200
    assert r.json()["mode"] == "sandbox"


def test_ntsl_arm(client, tmp_path, monkeypatch):
    monkeypatch.setattr("src.services.ntsl_arm.NTSL_DIR", tmp_path / "ntsl")
    r = client.post(
        "/api/v1/ntsl/arm",
        json={"symbol": "PETR4", "structure_type": "scalp", "side": "long"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "armed"


def test_kpi_history(client):
    for rng in ("today", "5d", "20d", "3mo"):
        r = client.get("/api/v1/kpi/history", params={"range": rng})
        assert r.status_code == 200
        assert r.json()["range"] == rng
