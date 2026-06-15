"""Structure builder API (3.0-beta)."""

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.models import init_db


@pytest.fixture
def client(monkeypatch):
    from src.main import create_app

    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("SCANNER_OLLAMA_ON_SCAN", "false")
    init_db()
    return TestClient(create_app())


def test_create_idea_from_structure(client):
    r = client.post(
        "/api/v1/ideas/from-structure",
        json={"symbol": "PETR4", "structure_type": "covered_call", "side": "long"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["symbol"] == "PETR4"
    assert data["structure_type"] == "covered_call"
    assert len(data["legs"]) >= 2
    assert "builder" in (data.get("rationale_tags") or [])


def test_structure_preview_partial(client):
    r = client.post(
        "/board/partials/symbol/PETR4/structure-preview",
        data={"structure_type": "vertical", "side": "long"},
    )
    assert r.status_code == 200
    assert "bb-legs" in r.text or "legs" in r.text.lower()


def test_structure_builder_in_symbol_panel(client):
    r = client.get("/board/partials/symbol/PETR4")
    assert r.status_code == 200
    assert "structure-builder" in r.text
    assert "covered_call" in r.text
