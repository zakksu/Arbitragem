"""3.0.0 GA — opportunity rail, layout, portfolio BT, NTSL, kill switch."""

from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import TradeIdea, get_session_factory, init_db
from src.services.ntsl_templates import ntsl_for_idea
from src.services.trade_ideas import TradeIdeaService


def _client():
    get_settings.cache_clear()
    init_db()
    return TestClient(create_app())


def test_opportunity_rail_endpoint():
    r = _client().get("/api/v1/signals/opportunity-rail")
    assert r.status_code == 200
    data = r.json()
    assert "signals" in data
    assert any(s["id"] == "petr_prio" for s in data["signals"])


def test_portfolio_backtest_endpoint():
    r = _client().get("/api/v1/portfolio/backtest")
    assert r.status_code == 200
    data = r.json()
    assert "portfolio_profit_factor" in data
    assert "gates_pass" in data
    assert data["period_days"] == 30


def test_board_layouts_list_and_activate():
    c = _client()
    r = c.get("/api/v1/board/layouts")
    assert r.status_code == 200
    layouts = r.json()["layouts"]
    assert len(layouts) >= 3
    r2 = c.post("/api/v1/board/layout/options_hedge")
    assert r2.status_code == 200
    assert r2.json()["preset"] == "options_hedge"
    active = c.get("/api/v1/board/layout/active").json()
    assert active["preset"] == "options_hedge"


def test_pause_all_closes_sleeves_without_rejecting_ideas():
    from src.services.trading_sleeves import set_all

    set_all(True)
    session = get_session_factory()()
    idea = TradeIdea(
        symbol="PETR4",
        title="test",
        side="long",
        structure_type="scalp",
        legs=[{"symbol": "PETR4", "side": "buy", "quantity": 100, "leg_type": "cash"}],
        status="detected",
    )
    session.add(idea)
    session.commit()
    idea_id = idea.id
    session.close()

    r = _client().post("/api/v1/strategies/pause-all")
    assert r.status_code == 200
    assert r.json().get("rejected_ideas", 0) == 0

    session = get_session_factory()()
    updated = session.get(TradeIdea, idea_id)
    assert updated.status == "detected"
    session.close()


def test_ntsl_templates_per_structure():
    for st in ("covered_call", "vertical", "collar", "bova_hedge", "pair_spread"):
        idea = TradeIdea(
            id=1,
            symbol="PETR4",
            structure_type=st,
            side="long",
            legs=[
                {"symbol": "PETR4", "side": "buy", "quantity": 100, "leg_type": "cash"},
                {"symbol": "PETRX120", "side": "sell", "quantity": 100, "leg_type": "call", "strike": 120},
            ],
        )
        code = ntsl_for_idea(idea)
        assert f"3.0" in code
        assert "Leg 1" in code or "Leg" in code


def test_bova_hedge_sizing_in_legs():
    session = get_session_factory()()
    try:
        svc = TradeIdeaService(session)
        legs = svc._legs_for_structure("bova_hedge", "PETR4", "long", None)
        assert len(legs) >= 1
        bova = next((l for l in legs if l.get("leg_type") == "bova_put"), None)
        if bova:
            assert bova["quantity"] >= 1
            assert "hedge_ratio" in bova
    finally:
        session.close()


def test_opportunity_rail_partial():
    r = _client().get("/board/partials/opportunity-rail")
    assert r.status_code == 200
    assert "bb-opportunity-rail" in r.text


def test_portfolio_backtest_partial():
    r = _client().get("/board/partials/portfolio-backtest")
    assert r.status_code == 200
    assert "Portfolio backtest" in r.text


def test_layout_presets_partial():
    r = _client().get("/board/partials/layout-presets")
    assert r.status_code == 200
    assert "bb-layout-presets" in r.text


def test_confirm_logs_system_event():
    from src.services.kill_switch import set_active

    set_active(False)
    session = get_session_factory()()
    idea = TradeIdea(
        symbol="VALE3",
        title="vale test",
        side="long",
        structure_type="scalp",
        legs=[{"symbol": "VALE3", "side": "buy", "quantity": 100, "leg_type": "cash"}],
        status="backtested",
        backtest_proof={"profit_factor": 1.5, "max_drawdown_pct": 5.0},
    )
    session.add(idea)
    session.commit()
    idea_id = idea.id
    session.close()

    c = _client()
    r = c.post(f"/api/v1/ideas/{idea_id}/confirm")
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

    events = c.get("/api/v1/system/events?limit=5").json()
    assert any(e.get("component") == "trade_ideas" for e in events)


def test_version_is_4_0_beta():
    from src import __version__

    assert __version__ == "14.0.0"
    r = _client().get("/api/v1/health/live")
    assert r.json()["version"] == "14.0.0"
