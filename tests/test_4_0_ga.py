"""4.0.0 GA — paper validation gate + journal export."""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import ScanResult, Trade, TradeIdea, get_session_factory, init_db
from src.services.paper_validation import build_paper_validation, build_journal_export


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ga.db'}")
    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    init_db()
    return TestClient(create_app())


def test_paper_validation_gate_fail(client):
    r = client.get("/api/v1/paper/validation")
    assert r.status_code == 200
    data = r.json()
    assert data["gate_pass"] is False
    assert data["week"] == "paper_week_3"
    assert len(data["checklist"]) == 4
    assert data["paper_trading_mode"] is True


def test_paper_validation_gate_pass(client):
    db = get_session_factory()()
    try:
        for i in range(10):
            scan = ScanResult(
                symbol="PETR4",
                scan_date=datetime.utcnow(),
                spike_score=70.0,
                alert_level="info",
            )
            db.add(scan)
            db.flush()
            db.add(
                TradeIdea(
                    symbol="PETR4",
                    structure_type="scalp" if i < 7 else "vertical",
                    status="confirmed",
                    reliability=80.0,
                    rationale=f"Trade Product note #{i}",
                    scan_result_id=scan.id,
                )
            )
        db.commit()
    finally:
        db.close()

    data = client.get("/api/v1/paper/validation").json()
    assert data["gate_pass"] is True
    assert data["counts"]["structure_confirms"] >= 10
    assert data["counts"]["trade_products_journaled"] >= 3


def test_journal_export_json(client):
    db = get_session_factory()()
    try:
        db.add(
            Trade(
                symbol="PETR4",
                side="buy",
                quantity=100,
                price=38.0,
                executed_at=datetime.utcnow(),
                source="paper",
                external_id="GA-1",
            )
        )
        db.commit()
    finally:
        db.close()

    r = client.get("/api/v1/paper/journal/export")
    assert r.status_code == 200
    data = r.json()
    assert len(data["trades"]) == 1
    assert "validation" in data


def test_journal_export_csv(client):
    r = client.get("/api/v1/paper/journal/export", params={"format": "csv"})
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "symbol" in r.text


def test_journal_export_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.services.paper_validation._JOURNAL_DIR",
        tmp_path / "journal",
    )
    r = client.post("/api/v1/paper/journal/export")
    assert r.status_code == 200
    body = r.json()
    assert body["format"] == "csv"
    assert body["rows"] >= 0


def test_version_is_4_1_alpha():
    from src import __version__

    assert __version__ == "12.0.0-alpha"


def test_status_shows_paper_gate_banner(client):
    r = client.get("/board/partials/status")
    assert r.status_code == 200
    assert "bb-paper-gate" in r.text or "Paper week" in r.text
    import scripts.paper_validation as pv

    assert callable(pv.main)


def test_build_paper_validation_unit(db_session):
    report = build_paper_validation(db_session)
    assert report["gate_pass"] is False
    assert build_journal_export(db_session)["trades"] == []


@pytest.fixture
def db_session(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ga2.db'}")
    get_settings.cache_clear()
    init_db()
    session = get_session_factory()()
    yield session
    session.close()
