"""3.0-alpha — structure model, max pain, options chain, multi-leg NTSL."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.models import TradeIdea, get_session_factory, init_db
from src.services.structure_signals import compute_max_pain
from src.services.trade_ideas import TradeIdeaService


@pytest.fixture
def client():
    from src.main import create_app

    return TestClient(create_app())


def test_compute_max_pain_stub_chain():
    chain = {
        "underlying": "PETR4",
        "underlying_last": 38.0,
        "calls": [
            {"strike": 37.0, "open_interest": 10000},
            {"strike": 38.0, "open_interest": 5000},
            {"strike": 39.0, "open_interest": 8000},
        ],
        "puts": [
            {"strike": 37.0, "open_interest": 7000},
            {"strike": 38.0, "open_interest": 12000},
            {"strike": 39.0, "open_interest": 4000},
        ],
    }
    signal = compute_max_pain(chain)
    assert signal is not None
    assert signal["max_pain_strike"] in (37.0, 38.0, 39.0)
    assert signal["underlying"] == "PETR4"


def test_structure_types_api(client):
    r = client.get("/api/v1/structures/types")
    assert r.status_code == 200
    data = r.json()
    assert data["max_pain_enabled"] is True
    ids = {t["id"] for t in data["structure_types"]}
    assert "covered_call" in ids
    assert "bova_hedge" in ids


def test_options_chain_endpoint(client):
    r = client.get("/api/v1/options/chain/PETR4")
    assert r.status_code == 200
    data = r.json()
    assert data["underlying"] == "PETR4"
    assert data.get("calls")
    assert data.get("puts")


def test_max_pain_signal_endpoint(client):
    r = client.get("/api/v1/signals/max-pain/PETR4")
    assert r.status_code == 200
    body = r.json()
    assert "max_pain" in body
    assert body["max_pain"]["max_pain_strike"]


def test_multi_leg_ntsl_export():
    get_settings.cache_clear()
    init_db()
    session = get_session_factory()()
    try:
        idea = TradeIdea(
            symbol="PETR4",
            structure_type="covered_call",
            side="long",
            legs=[
                {"symbol": "PETR4", "side": "buy", "quantity": 100, "leg_type": "cash"},
                {
                    "symbol": "PETRX39",
                    "side": "sell",
                    "quantity": 100,
                    "leg_type": "call",
                    "strike": 39.0,
                },
            ],
        )
        session.add(idea)
        session.flush()
        ntsl = TradeIdeaService._ntsl_for_idea(idea)
        assert "multi-leg covered_call" in ntsl
        assert "Leg1" in ntsl
        assert "Leg2" in ntsl
        assert "PETRX39" in ntsl
    finally:
        session.close()


def test_generate_ideas_with_structure_filter(client, monkeypatch):
    monkeypatch.setenv("SCANNER_MODE", "filipe_core14")
    monkeypatch.setenv("SCANNER_INCLUDE_BOVA_OPTIONS", "false")
    get_settings.cache_clear()
    client.post("/api/v1/scanner/run")
    r = client.post("/api/v1/ideas/generate?limit=3&structure_type=vertical")
    assert r.status_code == 200
    ideas = r.json().get("ideas", [])
    if ideas:
        assert ideas[0]["structure_type"] == "vertical"
