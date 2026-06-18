"""Live Radar + scalp cost gate (12.0 GA)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import TradeIdea, get_session_factory, init_db
from src.services.live_radar import build_live_radar
from src.services.scalp_cost_gate import scalp_cost_gate


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'radar.db'}")
    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("PAPER_TRADING_MODE", "true")
    init_db()
    return TestClient(create_app())


def test_build_live_radar_shape():
    radar = build_live_radar()
    assert "lamps" in radar
    assert set(radar["lamps"]) == {"api", "bridge", "motor", "scanner", "mind", "sleeves"}
    assert "ready_to_scan" in radar
    assert "ready_to_execute" in radar
    assert "phase_c" in radar
    if not radar.get("ready_to_execute"):
        assert "phase_c_gate" in radar["blockers"] or radar.get("paper_trading_mode")
    assert "blockers" in radar
    assert isinstance(radar["outbox"], dict)


def test_ops_live_radar_api(client: TestClient):
    r = client.get("/api/v1/ops/live-radar")
    assert r.status_code == 200
    body = r.json()
    assert body["lamps"]["api"]["state"] in ("green", "yellow", "red")


def test_live_radar_partial(client: TestClient):
    r = client.get("/board/partials/live-radar")
    assert r.status_code == 200
    assert "Live Radar" in r.text


def test_scalp_cost_gate_breakeven():
    gate = scalp_cost_gate(
        {"symbol": "PETR4", "side": "long", "entry_price": 38.0, "target_price": 38.02, "stop_price": 37.95}
    )
    assert gate["min_ticks_required"] >= 1
    assert gate["target_ticks"] == 2
    assert gate["ok"] is False

    ok_gate = scalp_cost_gate(
        {"symbol": "PETR4", "side": "long", "entry_price": 38.0, "target_price": 38.10, "stop_price": 37.95}
    )
    assert ok_gate["ok"] is True


def test_confirm_blocks_below_breakeven(client: TestClient):
    session = get_session_factory()()
    idea = TradeIdea(
        symbol="PETR4",
        title="breakeven gate",
        side="long",
        structure_type="scalp",
        entry_price=38.0,
        target_price=38.02,
        stop_price=37.95,
        legs=[{"symbol": "PETR4", "side": "buy", "quantity": 100, "leg_type": "cash"}],
        status="backtested",
        backtest_proof={"profit_factor": 2.0, "max_drawdown_pct": 3.0},
    )
    session.add(idea)
    session.commit()
    idea_id = idea.id
    session.close()

    r = client.post(f"/api/v1/ideas/{idea_id}/confirm")
    assert r.status_code == 400
    detail = r.json().get("detail", "")
    assert "tick" in detail.lower() or "breakeven" in detail.lower()
