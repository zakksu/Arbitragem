"""Backtest rankings service tests."""

from datetime import datetime

from src.autonomous.backtest_rankings import BacktestRankingsService
from src.models import OptimizationRun, Strategy


def test_sync_rankings_from_wfo_run(db_session):
    import uuid

    strategy = Strategy(name=f"lab_test_{uuid.uuid4().hex[:8]}", status="active", parameters={"fast": 5})
    db_session.add(strategy)
    db_session.commit()

    run = OptimizationRun(
        strategy_id=strategy.id,
        method="walk_forward",
        status="completed",
        parameter_space={"symbol": "PETR4", "folds": 3},
        best_parameters={"fast": 8, "slow": 21},
        best_metrics={
            "profit_factor": 1.8,
            "max_drawdown_pct": 4.2,
            "win_rate": 58.0,
            "net_pnl": 500.0,
        },
        results={
            "folds": [
                {"fold": 1, "train_pnl": 100, "test_pnl": 50},
                {"fold": 2, "train_pnl": 80, "test_pnl": 30},
            ]
        },
        completed_at=datetime.utcnow(),
    )
    db_session.add(run)
    db_session.commit()

    svc = BacktestRankingsService(db_session)
    n = svc.sync_from_optimization_runs()
    assert n >= 1

    rows = svc.list_rankings(symbol="PETR4")
    assert len(rows) >= 1
    assert rows[0]["symbol"] == "PETR4"
    assert rows[0]["profit_factor"] == 1.8


def test_rankings_api_list(client, db_session):
    test_sync_rankings_from_wfo_run(db_session)
    r = client.get("/api/v1/backtest/rankings?symbol=PETR4")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 1
    assert body["rankings"][0]["symbol"] == "PETR4"


def test_rankings_promote_gate(client, db_session):
    from src.models import BacktestRanking

    r = BacktestRanking(
        symbol="VALE3",
        structure_type="scalp_long",
        profit_factor=1.0,
        max_drawdown_pct=4.0,
        win_rate=50.0,
        status="active",
    )
    db_session.add(r)
    db_session.commit()
    rid = r.id

    resp = client.post(f"/api/v1/backtest/rankings/{rid}/promote")
    assert resp.status_code == 400
    assert "gate" in resp.json()["detail"].lower()
