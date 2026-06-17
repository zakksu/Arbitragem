"""4.0-rc — Profit co-start, paper slippage preview, education, KPI history."""

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import Trade, get_session_factory, init_db
from src.services.education import daily_axiom, list_axioms, structure_blurb
from src.services.paper_execution import estimate_paper_fills
from src.services.kpi_history import build_kpi_history


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'rc.db'}")
    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("SCANNER_OLLAMA_ON_SCAN", "false")
    init_db()
    return TestClient(create_app())


def test_education_axioms_pack():
    axioms = list_axioms()
    assert len(axioms) >= 3
    daily = daily_axiom()
    assert "title" in daily and "body" in daily


def test_structure_blurb():
    blurb = structure_blurb("covered_call")
    assert blurb is not None
    assert "blurb" in blurb


def test_education_api(client):
    r = client.get("/api/v1/education")
    assert r.status_code == 200
    data = r.json()
    assert "axioms" in data and "structures" in data
    r2 = client.get("/api/v1/education/structures/vertical")
    assert r2.status_code == 200


def test_paper_fill_preview_model():
    preview = estimate_paper_fills(
        {
            "symbol": "PETR4",
            "side": "long",
            "entry_price": 38.0,
            "legs": [{"symbol": "PETR4", "side": "buy", "quantity": 100}],
        }
    )
    assert preview["slippage_model"] == "spread_plus_1_tick"
    assert len(preview["legs"]) == 1
    leg = preview["legs"][0]
    assert leg["ideal_price"] > 0
    assert leg["expected_fill"] != leg["ideal_price"] or leg["slippage_ticks"] >= 0


def test_confirm_includes_paper_fill_preview(client, monkeypatch):
    from src.models import ScanResult, TradeIdea
    from datetime import datetime

    db = get_session_factory()()
    scan = ScanResult(
        symbol="PETR4",
        scan_date=datetime.utcnow(),
        spike_score=70.0,
        alert_level="info",
    )
    db.add(scan)
    db.flush()
    idea = TradeIdea(
        symbol="PETR4",
        structure_type="scalp",
        side="long",
        status="backtested",
        reliability=80.0,
        entry_price=38.0,
        backtest_proof={"profit_factor": 1.5, "max_drawdown_pct": 5.0},
        scan_result_id=scan.id,
    )
    db.add(idea)
    db.commit()
    r = client.post(f"/api/v1/ideas/{idea.id}/confirm")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"
    assert "paper_fill_preview" in data
    assert data["paper_fill_preview"]["total_slippage_brl"] >= 0
    db.close()


def test_kpi_history_ytd_and_slippage(client):
    r = client.get("/api/v1/kpi/history", params={"range": "ytd"})
    assert r.status_code == 200
    assert r.json()["range"] == "ytd"
    assert "avg_slippage_ticks" in r.json()


def test_kpi_slippage_from_trades(db_session):
    from datetime import datetime

    db_session.add(
        Trade(
            symbol="PETR4",
            side="buy",
            quantity=100,
            price=38.03,
            pnl=10.0,
            executed_at=datetime.utcnow(),
            external_id="RC-1",
            raw_payload={
                "slippage_model": "spread_plus_1_tick",
                "quote_bid": 38.0,
                "quote_ask": 38.02,
            },
        )
    )
    db_session.commit()
    hist = build_kpi_history(db_session, "today")
    assert hist.get("avg_slippage_ticks") is not None


@pytest.fixture
def db_session(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'rc2.db'}")
    get_settings.cache_clear()
    init_db()
    session = get_session_factory()()
    yield session
    session.close()


def test_setup_profitchart_step(client):
    r = client.get("/api/v1/setup/status")
    ids = [s["id"] for s in r.json()["steps"]]
    assert "profitchart" in ids


def test_dev_profitchart_co_start(monkeypatch, tmp_path):
    import scripts.dev as dev

    fake_exe = tmp_path / "ProfitChart.exe"
    fake_exe.write_bytes(b"stub")
    monkeypatch.setenv("PROFITCHART_EXE", str(fake_exe))
    monkeypatch.setattr(dev, "sys", __import__("sys"))
    monkeypatch.setattr(dev.sys, "platform", "win32")
    launched = []

    def fake_popen(cmd, **kwargs):
        launched.append(cmd)
        return None

    monkeypatch.setattr(dev.subprocess, "Popen", fake_popen)
    get_settings.cache_clear()
    dev._maybe_start_profitchart()
    assert launched
