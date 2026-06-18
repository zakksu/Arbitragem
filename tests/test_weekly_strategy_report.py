"""Weekly strategy simulation report."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import ReplaySession, init_db
from src.services.weekly_strategy_sim import build_weekly_strategy_report, format_weekly_report_markdown


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'tweekly.db'}")
    get_settings.cache_clear()
    init_db()
    return TestClient(create_app())


@pytest.fixture
def db_session(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'tweekly2.db'}")
    get_settings.cache_clear()
    init_db()
    from src.models import get_session_factory

    session = get_session_factory()()
    yield session
    session.close()


def test_weekly_report_empty(db_session):
    report = build_weekly_strategy_report(db_session, days=7, run_sim=False)
    assert report["period_days"] == 7
    assert "summary" in report
    assert "strategies" in report
    md = format_weekly_report_markdown(report)
    assert "Weekly strategy simulation" in md


def test_weekly_report_with_replay(db_session):
    row = ReplaySession(
        job_id="wk1",
        symbol="PETR4",
        strategy_name="s1_vwap_reclaim",
        status="completed",
        fill_count=4,
        metrics={
            "total_pnl": 120.0,
            "wins": 3,
            "losses": 1,
            "win_rate_pct": 75.0,
            "round_trips": 4,
        },
        completed_at=datetime.utcnow(),
    )
    db_session.add(row)
    db_session.commit()

    report = build_weekly_strategy_report(db_session, days=7, run_sim=False)
    assert len(report["strategies"]) >= 1
    assert report["strategies"][0]["symbol"] == "PETR4"


def test_weekly_report_api(client: TestClient):
    r = client.get("/api/v1/strategies/weekly-report?days=7")
    assert r.status_code == 200
    body = r.json()
    assert body["period_days"] == 7
    assert "summary" in body
