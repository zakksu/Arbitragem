"""4.0-alpha — P&L truth, risk profile API, ProfitDLL detect."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.integrations.profit_dll_detect import detect_profit_dll
from src.models import Trade, get_session_factory, init_db
from src.services.pnl_truth import resolve_day_pnl
from src.services.risk_profile import get_or_create_profile, profile_to_dict


@pytest.fixture
def client(monkeypatch, tmp_path):
    from src.main import create_app

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("PROFIT_BRIDGE_AUTO_DETECT", "false")
    init_db()
    return TestClient(create_app())


def test_risk_profile_defaults(client):
    r = client.get("/api/v1/risk/profile")
    assert r.status_code == 200
    data = r.json()
    assert data["max_daily_loss_brl"] == pytest.approx(500.0)
    assert data["max_open_positions"] >= 1
    assert data["cost_per_trade_brl"] == pytest.approx(50.0)
    assert "sector_caps" in data


def test_risk_profile_put(client):
    r = client.put(
        "/api/v1/risk/profile",
        json={"max_daily_loss_brl": 750.0, "sector_caps": {"default": 35.0, "energia": 30.0}},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["max_daily_loss_brl"] == pytest.approx(750.0)
    assert data["sector_caps"]["energia"] == pytest.approx(30.0)


def test_profit_pnl_endpoint(client):
    r = client.get("/api/v1/profit/pnl")
    assert r.status_code == 200
    data = r.json()
    assert "day_pnl" in data
    assert data["pnl_source"] in ("journal", "profit", "clear")
    assert "trades_today" in data


def test_profit_dll_detect_structure():
    result = detect_profit_dll()
    assert isinstance(result["found"], bool)
    assert "candidates" in result


def test_pnl_journal_priority(db_session):
    db_session.add(
        Trade(
            symbol="PETR4",
            side="buy",
            quantity=100,
            price=36.0,
            pnl=99.0,
            executed_at=datetime.utcnow(),
            external_id="T-4A-1",
        )
    )
    db_session.commit()
    pnl = resolve_day_pnl(db_session)
    assert pnl["pnl_source"] == "journal"
    assert pnl["day_pnl"] == pytest.approx(99.0)


@pytest.fixture
def db_session(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'session.db'}")
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    init_db()
    session = get_session_factory()()
    yield session
    session.close()


def test_profile_singleton(db_session):
    p1 = get_or_create_profile(db_session)
    p2 = get_or_create_profile(db_session)
    assert p1.id == p2.id
    d = profile_to_dict(p1)
    assert d["max_net_delta"] == pytest.approx(0.5)
