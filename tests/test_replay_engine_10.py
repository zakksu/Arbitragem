"""10.0 — Replay Training Engine + Strategy Store."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import ReplaySession, StoredStrategy, init_db
from src.services.ntsl_parser import extract_ntsl_features
from src.services.replay_engine import start_replay
from src.services.strategy_store import scan_ntsl_file


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'replay10.db'}")
    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("REPLAY_OLLAMA_SUMMARY", "false")
    monkeypatch.setenv("REPLAY_FEED_WFO", "false")
    init_db()
    return TestClient(create_app())


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'replay10b.db'}")
    get_settings.cache_clear()
    init_db()
    from src.models import get_session_factory

    session = get_session_factory()()
    yield session
    session.close()


SAMPLE_NTSL = """// Scalp PETR4 test
input
  StopTicks(5);
  TargetTicks(8);
var
  EntryPrice : Float;
begin
  EntryPrice := Close;
  // Leg 1: buy stock
  // BuyAtMarket(100, "PETR4");
  SetStopLoss(StopTicks * MinPriceIncrement);
end;
"""


def test_ntsl_parser_extracts_features():
    feat = extract_ntsl_features(SAMPLE_NTSL)
    assert "PETR4" in feat["symbols"]
    assert feat["inputs"]
    assert "scalp" in feat["summary"].lower() or feat["line_count"] > 5


def test_strategy_store_indexes_file(db_session, tmp_path):
    path = tmp_path / "petr4_scalp.ntsl"
    path.write_text(SAMPLE_NTSL, encoding="utf-8")
    row = scan_ntsl_file(db_session, path)
    db_session.commit()
    assert row.id
    assert row.extracted_logic
    assert "PETR4" in (row.symbols or [])


def test_replay_tick_sim_produces_fills(db_session):
    run = start_replay(
        strategy="scalp_default",
        symbol="PETR4",
        speed=10.0,
        mode="sandbox",
        session=db_session,
    )
    assert run["status"] == "completed"
    assert run["source"] == "tick_sim"
    assert run["job_id"]
    row = db_session.query(ReplaySession).filter(ReplaySession.job_id == run["job_id"]).first()
    assert row is not None
    assert row.fill_count >= 0


def test_replay_api_run(client):
    r = client.post(
        "/api/v1/replay/run",
        json={"strategy": "scalp_default", "symbol": "PETR4", "speed": 10, "mode": "sandbox"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "PETR4"
    assert body["status"] in ("completed", "running", "queued")


def test_engine_mind_endpoint(client):
    r = client.get("/api/v1/engine/mind")
    assert r.status_code == 200
    body = r.json()
    assert "phase" in body
    assert "sources" in body
    assert body["sources"]["replay_training"] is True


def test_strategy_store_scan_api(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ss.db'}")
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("STRATEGY_STORE_EXTRA_DIRS", str(tmp_path / "ntsl"))
    get_settings.cache_clear()
    ntsl_dir = tmp_path / "ntsl"
    ntsl_dir.mkdir()
    (ntsl_dir / "vale3.ntsl").write_text(SAMPLE_NTSL.replace("PETR4", "VALE3"), encoding="utf-8")
    init_db()
    client = TestClient(create_app())
    r = client.post("/api/v1/strategy-store/scan")
    assert r.status_code == 200
    assert r.json().get("indexed", 0) >= 1
    r2 = client.get("/api/v1/strategy-store")
    assert r2.status_code == 200
    assert len(r2.json().get("strategies", [])) >= 1


def test_replay_sessions_list(client):
    client.post(
        "/api/v1/replay/run",
        json={"strategy": "scalp_default", "symbol": "PETR4", "speed": 5, "mode": "sandbox"},
    )
    r = client.get("/api/v1/replay/sessions")
    assert r.status_code == 200
    assert len(r.json().get("sessions", [])) >= 1


def test_bridge_replay_with_fills(client, monkeypatch):
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "true")
    monkeypatch.setenv("PROFIT_BRIDGE_URL", "http://localhost:9100")
    get_settings.cache_clear()
    r = client.post(
        "/api/v1/replay/run",
        json={"strategy": "scalp_default", "symbol": "PETR4", "speed": 10, "mode": "sandbox"},
    )
    assert r.status_code == 200
    body = r.json()
    if body.get("source") == "profit_bridge":
        assert body.get("status") == "completed"
        assert body.get("fill_count", 0) > 0


def test_knowledge_ingest_replays(client):
    client.post(
        "/api/v1/replay/run",
        json={"strategy": "scalp_default", "symbol": "PETR4", "speed": 5, "mode": "sandbox"},
    )
    r = client.post("/api/v1/knowledge/ingest/replays", params={"limit": 5})
    assert r.status_code == 200
    assert "indexed" in r.json()


def test_self_healing_breakers(client):
    r = client.get("/api/v1/self-healing/breakers")
    assert r.status_code == 200
    assert "breakers" in r.json()


def test_circuit_breaker_unit():
    from src.services.self_healing import get_breaker

    br = get_breaker("test_unit_breaker", failure_threshold=2, reset_sec=1.0)
    br.record_failure()
    br.record_failure()
    assert br.is_open() is True
    br.record_success()
    assert br.is_open() is False


def test_b3_excel_import(db_session, tmp_path):
    import pandas as pd

    from src.services.b3_history_import import import_b3_history_excel

    path = tmp_path / "history.xlsx"
    df = pd.DataFrame(
        {
            "Data": ["01/06/2025"],
            "Ativo": ["PETR4"],
            "Tipo": ["C"],
            "Quantidade": [100],
            "Preco": ["38,50"],
            "Resultado": ["50,00"],
        }
    )
    df.to_excel(path, index=False, engine="openpyxl")
    result = import_b3_history_excel(db_session, path)
    assert result.get("imported", 0) >= 1
    assert result.get("source_format") == "excel"
