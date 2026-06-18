"""FastAPI route handlers."""

from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.config import get_settings

from src.api.schemas import (
    AlertsStatusResponse,
    BacktestRequest,
    BacktestRunResponse,
    HealthResponse,
    OllamaChatRequest,
    OptimizationRunResponse,
    OptimizeRequest,
    ProfitBacktestRunRequest,
    ProfitPnlResponse,
    ReplayRunRequest,
    NtslArmRequest,
    RiskProfileResponse,
    RiskProfileUpdate,
    RiskSummaryResponse,
    ScanResultResponse,
    StrategyCreate,
    StrategyResponse,
    StrategyRiskUpdate,
    StrategyUpdate,
    StructureIdeaRequest,
    SystemEventResponse,
    TradeResponse,
)
from src import __version__
from src.integrations.clear_api import get_clear_client
from src.integrations.ollama_client import get_ollama_client
from src.integrations.profit_bridge import get_profit_client
from src.integrations.profit_parser import parse_profit_backtest_csv, save_uploaded_csv
from src.models import BacktestRun, OptimizationRun, ScanResult, Strategy, SystemEvent, Trade, get_session_factory
from src.services.backtest import BacktestService
from src.services.journal import JournalService
from src.services.alerting import get_alert_service
from src.services.optimizer import OptimizerService
from src.services.risk_summary import build_risk_summary
from src.services.risk_profile import get_or_create_profile, profile_to_dict, update_profile
from src.services.pnl_truth import resolve_day_pnl
from src.services.risk_cockpit import build_risk_cockpit
from src.services.scanner import PatternScanner
from src.services.strategy_manager import StrategyService
from src.services.trade_ideas import TradeIdeaService
from src.services.walk_forward import WalkForwardOptimizer
from src.services.walk_forward_promotion import run_walk_forward_promotion

router = APIRouter()


def get_db():
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@router.get("/health/live")
def health_live():
    """Fast liveness probe — no external service calls."""
    return {"status": "ok", "version": __version__}


@router.get("/bootstrap")
def bootstrap(db: Session = Depends(get_db)):
    """One fast call for dashboard shell — DB + config only, no Ollama/Profit probes."""
    from src.services.bootstrap_context import build_bootstrap

    return build_bootstrap(db)


@router.get("/integrations/status")
def integrations_status():
    """Slow probes isolated — call only from Settings or manual refresh."""
    import time

    settings = get_settings()
    cache = getattr(integrations_status, "_cache", None)
    now = time.time()
    if cache and now - cache["at"] < 60:
        return cache["data"]

    data = {
        "ollama": get_ollama_client().is_available() if settings.ollama_runtime_enabled else False,
        "profit_bridge": get_profit_client().is_available(),
        "clear_api": get_clear_client().is_configured(),
    }
    integrations_status._cache = {"at": now, "data": data}
    return data


@router.get("/health", response_model=HealthResponse)
def health_check():
    import time

    settings = get_settings()
    alerts = get_alert_service()
    now = time.time()
    cache = getattr(health_check, "_cache", None)
    if cache and now - cache["at"] < 30:
        ollama_ok, profit_ok = cache["ollama"], cache["profit"]
    else:
        ollama_ok = get_ollama_client().is_available() if settings.ollama_runtime_enabled else False
        profit_ok = get_profit_client().is_available()
        health_check._cache = {"at": now, "ollama": ollama_ok, "profit": profit_ok}
    return HealthResponse(
        status="ok",
        version=__version__,
        ollama=ollama_ok,
        profit_bridge=profit_ok,
        clear_api=get_clear_client().is_configured(),
        alerts_enabled=settings.alerts_enabled,
        alerts_configured=alerts.enabled,
        paper_trading_mode=settings.paper_trading_mode,
        scanner_mode=settings.scanner_mode,
        scanner_symbol_count=len(settings.scanner_symbol_list),
    )


@router.get("/alerts/status", response_model=AlertsStatusResponse)
def alerts_status():
    settings = get_settings()
    svc = get_alert_service()
    return AlertsStatusResponse(
        enabled=settings.alerts_enabled,
        configured=svc.enabled,
        telegram=bool(settings.telegram_bot_token and settings.telegram_chat_id),
        discord=bool(settings.discord_webhook_url),
    )


@router.post("/alerts/test")
def alerts_test():
    svc = get_alert_service()
    if not svc.enabled:
        raise HTTPException(
            400,
            "Alerts not configured. Set ALERTS_ENABLED=true and Telegram or Discord in .env",
        )
    svc.notify("Test alert", "Arbitragem dashboard alerts are working.", "info")
    return {"sent": True}


@router.get("/strategies", response_model=list[StrategyResponse])
def list_strategies(db: Session = Depends(get_db)):
    return StrategyService(db).list_strategies()


@router.post("/strategies", response_model=StrategyResponse)
def create_strategy(payload: StrategyCreate, db: Session = Depends(get_db)):
    strategy = Strategy(**payload.model_dump())
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


@router.patch("/strategies/{strategy_id}", response_model=StrategyResponse)
def update_strategy(
    strategy_id: int,
    payload: StrategyUpdate,
    db: Session = Depends(get_db),
):
    try:
        data = payload.model_dump(exclude_unset=True)
        return StrategyService(db).update_strategy(strategy_id, data)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/strategies/{strategy_id}/pause", response_model=StrategyResponse)
def pause_strategy(strategy_id: int, db: Session = Depends(get_db)):
    try:
        return StrategyService(db).pause_strategy(strategy_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/strategies/{strategy_id}/start", response_model=StrategyResponse)
def start_strategy(strategy_id: int, db: Session = Depends(get_db)):
    try:
        return StrategyService(db).start_strategy(strategy_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/strategies/{strategy_id}/stop", response_model=StrategyResponse)
def stop_strategy(strategy_id: int, db: Session = Depends(get_db)):
    try:
        return StrategyService(db).stop_strategy(strategy_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/strategies/{strategy_id}/export-profit")
def export_to_profit(strategy_id: int, db: Session = Depends(get_db)):
    try:
        path = StrategyService(db).export_to_profit(strategy_id)
        return {"exported_path": path}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/strategies/{strategy_id}/risk", response_model=StrategyResponse)
def update_strategy_risk(
    strategy_id: int,
    payload: StrategyRiskUpdate,
    db: Session = Depends(get_db),
):
    strategy = db.get(Strategy, strategy_id)
    if not strategy:
        raise HTTPException(404, "Strategy not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(strategy, key, value)
    db.commit()
    db.refresh(strategy)
    return strategy


@router.get("/positions")
def list_positions():
    return get_clear_client().get_positions()


@router.get("/trades", response_model=list[TradeResponse])
def list_trades(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Trade).order_by(Trade.executed_at.desc()).limit(limit).all()


@router.post("/journal/sync")
def sync_journal(db: Session = Depends(get_db)):
    return JournalService(db).sync_all_sources()


@router.get("/scanner/results", response_model=list[ScanResultResponse])
def list_scan_results(
    limit: int = 200,
    symbol: str | None = None,
    latest_batch: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(ScanResult).order_by(ScanResult.scan_date.desc(), ScanResult.spike_score.desc())
    if symbol:
        query = query.filter(ScanResult.symbol == symbol.strip().upper())
    if latest_batch:
        latest = db.query(ScanResult.scan_date).order_by(ScanResult.scan_date.desc()).first()
        if not latest:
            return []
        query = query.filter(ScanResult.scan_date == latest[0])
    return query.limit(limit).all()


@router.post("/scanner/run", response_model=list[ScanResultResponse])
def run_scanner(db: Session = Depends(get_db)):
    results = PatternScanner(db).run_daily_scan()
    if results:
        get_alert_service().notify_scan_alerts(results)
        TradeIdeaService(db).generate_from_latest_scan(limit=12)
    return results


@router.get("/scanner/insights")
def scanner_insights(limit: int = 5, db: Session = Depends(get_db)):
    return {
        "insights": PatternScanner(db).get_scalp_insights(limit=min(limit, 20)),
        "scanner_mode": get_settings().scanner_mode,
    }


@router.get("/universe/ibov-top20")
def ibov_top20():
    from src.services.ibov_universe import load_ibov_top20

    symbols = load_ibov_top20()
    return {
        "count": len(symbols),
        "symbols": [s.to_dict() for s in symbols],
    }


@router.get("/universe/filipe-core14")
def filipe_core14():
    from src.services.filipe_universe import BOVA_UNDERLYING, SECTOR_BASKETS, load_filipe_core14

    symbols = load_filipe_core14()
    settings = get_settings()
    return {
        "count": len(symbols),
        "symbols": [s.to_dict() for s in symbols],
        "bova_underlying": BOVA_UNDERLYING,
        "stock_options_enabled": settings.scanner_include_stock_options,
        "bova_options_enabled": settings.scanner_include_bova_options,
        "sector_baskets": SECTOR_BASKETS,
    }


@router.get("/ideas")
def list_trade_ideas(
    limit: int = 20,
    status: str | None = None,
    symbol: str | None = None,
    db: Session = Depends(get_db),
):
    svc = TradeIdeaService(db)
    ideas = svc.list_ideas(limit=min(limit, 50), status=status, symbol=symbol)
    out = [svc.to_dict(i) for i in ideas]
    return {"ideas": out, "count": len(out), "symbol": symbol}


@router.post("/ideas/generate")
def generate_trade_ideas(
    limit: int = 12,
    structure_type: str | None = None,
    db: Session = Depends(get_db),
):
    svc = TradeIdeaService(db)
    created = svc.generate_from_latest_scan(
        limit=min(limit, 30), structure_type=structure_type
    )
    return {"generated": len(created), "ideas": [svc.to_dict(i) for i in created]}


@router.post("/ideas/from-structure")
def create_idea_from_structure(payload: StructureIdeaRequest, db: Session = Depends(get_db)):
    svc = TradeIdeaService(db)
    idea = svc.create_from_structure(
        payload.symbol, payload.structure_type, payload.side
    )
    return svc.to_dict(idea)


@router.post("/ideas/{idea_id}/confirm")
def confirm_trade_idea(
    idea_id: int,
    paper_override: bool = False,
    db: Session = Depends(get_db),
):
    from src.config import get_settings
    from src.services.paper_execution import estimate_paper_fills

    try:
        svc = TradeIdeaService(db)
        idea = svc.confirm_idea(idea_id, paper_override=paper_override)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    payload = svc.to_dict(idea)
    if get_settings().paper_trading_mode:
        payload["paper_fill_preview"] = estimate_paper_fills(payload)
    from src.services.idea_gates import build_idea_gates

    payload["gates"] = build_idea_gates(db, idea_id)
    return payload


@router.post("/ideas/{idea_id}/execute")
def execute_trade_idea(idea_id: int, db: Session = Depends(get_db)):
    from src.config import get_settings
    from src.services.idea_gates import build_idea_gates
    from src.services.paper_execution import estimate_paper_fills

    try:
        idea = TradeIdeaService(db).execute_idea(idea_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    payload = TradeIdeaService(db).to_dict(idea)
    if get_settings().paper_trading_mode:
        payload["paper_fill_preview"] = estimate_paper_fills(payload)
    payload["gates"] = build_idea_gates(db, idea_id)
    return payload


@router.get("/symbols/{symbol}/report")
def symbol_report(symbol: str, force: bool = False, db: Session = Depends(get_db)):
    from src.services.symbol_report import build_symbol_report

    return build_symbol_report(db, symbol, force=force)


@router.get("/symbols/{symbol}/session-vwap")
def symbol_session_vwap(symbol: str):
    from src.services.vwap import build_session_vwap_payload

    return build_session_vwap_payload(symbol)


@router.get("/ideas/{idea_id}")
def get_trade_idea(idea_id: int, db: Session = Depends(get_db)):
    from src.models import TradeIdea

    idea = db.get(TradeIdea, idea_id)
    if not idea:
        raise HTTPException(404, "Idea not found")
    return TradeIdeaService(db).to_dict(idea)


@router.get("/ideas/{idea_id}/gates")
def get_idea_gates(idea_id: int, db: Session = Depends(get_db)):
    from src.services.idea_gates import build_idea_gates

    try:
        return build_idea_gates(db, idea_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/execution/clear/status")
def execution_clear_status():
    from src.services.clear_router import clear_router_status

    return clear_router_status()


@router.get("/costs/scalp/{symbol}")
def scalp_cost_estimate(symbol: str, price: float, quantity: int = 100, leverage: float = 50.0):
    """B3/Clear fee + breakeven estimate for stock day-trade scalp."""
    from src.services.clear_cost_model import cost_summary_for_symbol

    return cost_summary_for_symbol(symbol, price, quantity=quantity, leverage=leverage)


@router.get("/board/{symbol}/notes")
def get_board_notes(symbol: str, db: Session = Depends(get_db)):
    from src.services.board_notes import BoardNotesService

    return BoardNotesService(db).to_dict(BoardNotesService(db).get(symbol))


@router.put("/board/{symbol}/notes")
def save_board_notes(
    symbol: str,
    payload: dict = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    from src.services.board_notes import BoardNotesService

    note = BoardNotesService(db).save(
        symbol, payload.get("content", ""), payload.get("levels")
    )
    return BoardNotesService(db).to_dict(note)


@router.post("/board/{symbol}/analyze")
def analyze_symbol(symbol: str, db: Session = Depends(get_db)):
    from src.services.board_notes import BoardNotesService

    sym = symbol.upper()
    quote = get_profit_client().get_quote(sym)
    ctx = f"Symbol {sym} last={quote.last if quote else '?'} volume={quote.volume if quote else 0}"
    report = get_ollama_client().analyze_trade(
        f"Blackboard report for {sym}: strengths, weaknesses, catalysts, 1-session scalp bias."
        f" Context: {ctx}"
    )
    note = BoardNotesService(db).save_ai_report(sym, report)
    return {"symbol": sym, "report": report, "note": BoardNotesService(db).to_dict(note)}


@router.post("/backtest/run")
def run_profit_backtest(payload: ProfitBacktestRunRequest):
    """Proxy to Profit bridge POST /backtest/run — returns job id + metrics."""
    metrics = get_profit_client().run_backtest(
        payload.symbol,
        payload.strategy,
        payload.period,
    )
    return metrics


@router.get("/options/bova")
def bova_options():
    return get_profit_client().get_bova_option_chain()


@router.get("/options/chain/{underlying}")
def unified_options_chain(underlying: str):
    client = get_profit_client()
    chain = client.get_option_chain(underlying)
    from src.services.structure_signals import compute_max_pain

    if "max_pain" not in chain:
        mp = compute_max_pain(chain)
        if mp:
            chain["max_pain"] = mp
    return chain


@router.get("/signals/max-pain/{underlying}")
def max_pain_signal(underlying: str):
    client = get_profit_client()
    chain = client.get_option_chain(underlying)
    from src.services.structure_signals import compute_max_pain

    signal = chain.get("max_pain") or compute_max_pain(chain)
    if not signal:
        raise HTTPException(404, "No option chain for underlying")
    iv = client.get_iv_rank(underlying)
    return {"max_pain": signal, "iv_rank": iv}


@router.get("/structures/types")
def structure_types():
    from src.services.structure_types import enabled_structure_types

    settings = get_settings()
    types = enabled_structure_types(settings.structure_types_enabled)
    return {
        "version": __version__,
        "structure_types": types,
        "greeks_stub_mode": settings.greeks_stub_mode,
        "max_pain_enabled": settings.max_pain_signal_enabled,
    }


@router.get("/options/greeks/{symbol}")
def option_greeks(symbol: str):
    return get_profit_client().get_greeks(symbol)


@router.get("/options/iv-rank/{underlying}")
def option_iv_rank(underlying: str):
    return get_profit_client().get_iv_rank(underlying)


@router.post("/walk-forward/promote")
def walk_forward_promote(db: Session = Depends(get_db)):
    """Manual walk-forward promotion — scans exports + fold gate."""
    settings = get_settings()
    return run_walk_forward_promotion(
        db, folds=settings.walk_forward_promote_folds
    )


@router.post("/walk-forward/run")
def run_walk_forward(payload: OptimizeRequest, db: Session = Depends(get_db)):
    """Walk-forward optimization — promotion input for 3.0."""
    strategy = db.get(Strategy, payload.strategy_id)
    if not strategy:
        raise HTTPException(404, "Strategy not found")
    space = _normalize_genetic_space(payload.parameter_space)
    run = WalkForwardOptimizer(db).run(
        strategy, payload.symbol, space, folds=payload.folds
    )
    return {
        "run_id": run.id,
        "method": run.method,
        "status": run.status,
        "best_parameters": run.best_parameters,
        "best_metrics": run.best_metrics,
        "results": run.results,
    }


@router.get("/options/stock/{underlying}")
def stock_options(underlying: str):
    return get_profit_client().get_stock_option_chain(underlying)


@router.post("/risk/kill-switch")
def risk_kill_switch(
    payload: dict = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    """Legacy alias — pauses all trading sleeves (does not reject ideas)."""
    from src.services.trading_sleeves import set_all
    from src.services.system_audit import log_event

    active = bool(payload.get("active", True))
    reason = str(payload.get("reason") or "Manual pause")
    state = set_all(not active, reason=reason if active else "")

    paused = 0
    if active:
        for s in db.query(Strategy).filter(Strategy.status == "active").all():
            try:
                StrategyService(db).pause_strategy(s.id)
                paused += 1
            except ValueError:
                pass
        log_event(
            db,
            level="warning",
            component="trading_sleeves",
            message=f"All sleeves paused — paused {paused} strategies",
            details={**state, "paused_strategies": paused},
        )
        db.commit()
    else:
        log_event(
            db,
            level="info",
            component="trading_sleeves",
            message="All sleeves open — confirms and executes allowed",
            details=state,
        )
        db.commit()

    return {
        "active": active,
        "activated_at": None,
        "reason": state.get("reason"),
        "sleeves": state.get("sleeves"),
        "paused_strategies": paused,
        "rejected_ideas": 0,
    }


@router.get("/risk/sleeves")
def get_trading_sleeves():
    from src.services.trading_sleeves import status as sleeves_status

    return sleeves_status()


@router.post("/risk/sleeves")
def post_trading_sleeves(payload: dict = Body(default_factory=dict), db: Session = Depends(get_db)):
    from src.services.system_audit import log_event
    from src.services.trading_sleeves import SLEEVES, set_all, set_sleeve, status as sleeves_status

    sleeve = payload.get("sleeve")
    open_ = payload.get("open")
    reason = str(payload.get("reason") or "")

    if sleeve:
        if open_ is None:
            raise HTTPException(400, "Provide 'open': true|false when setting a sleeve")
        state = set_sleeve(str(sleeve), bool(open_), reason=reason)
        log_event(
            db,
            level="info",
            component="trading_sleeves",
            message=f"Sleeve {sleeve} {'open' if open_ else 'paused'}",
            details=state,
        )
        db.commit()
        return state

    if "all_open" in payload:
        state = set_all(bool(payload["all_open"]), reason=reason)
        log_event(
            db,
            level="info",
            component="trading_sleeves",
            message=f"All sleeves {'open' if payload['all_open'] else 'paused'}",
            details=state,
        )
        db.commit()
        return state

    if "sleeves" in payload and isinstance(payload["sleeves"], dict):
        state = sleeves_status()
        for key in SLEEVES:
            if key in payload["sleeves"]:
                set_sleeve(key, bool(payload["sleeves"][key]), reason=reason)
        state = sleeves_status()
        db.commit()
        return state

    raise HTTPException(400, "Provide sleeve+open, all_open, or sleeves map")


@router.post("/autonomy/run")
def autonomy_run(db: Session = Depends(get_db)):
    from src.services.autonomy import run_autonomy_cycle

    return run_autonomy_cycle(db)


@router.get("/orchestrator/status")
def orchestrator_status_endpoint():
    from src.services.trading_orchestrator import orchestrator_status

    return orchestrator_status()


@router.post("/orchestrator/run")
def orchestrator_run(db: Session = Depends(get_db)):
    from src.services.trader_agent import run_trader_cycle

    return run_trader_cycle(db)


@router.get("/autonomy/status")
def autonomy_status_endpoint():
    from src.services.autonomy import autonomy_status

    return autonomy_status()


@router.get("/autonomy/gates")
def autonomy_gates(db: Session = Depends(get_db)):
    from src.services.autonomy_fast_track import autonomy_gate_snapshot

    return autonomy_gate_snapshot(db)


@router.post("/strategies/pause-all")
def pause_all_strategies(db: Session = Depends(get_db)):
    """Pause active strategies and close all sleeves — does not reject ideas."""
    from src.services.system_audit import log_event
    from src.services.trading_sleeves import set_all

    state = set_all(False, reason="pause-all")
    paused = 0
    for s in db.query(Strategy).filter(Strategy.status == "active").all():
        try:
            StrategyService(db).pause_strategy(s.id)
            paused += 1
        except ValueError:
            pass
    log_event(
        db,
        level="warning",
        component="trading_sleeves",
        message=f"Pause-all — closed sleeves, paused {paused} strategies",
        details={**state, "paused_strategies": paused},
    )
    db.commit()
    return {
        "paused": paused,
        "rejected_ideas": 0,
        "active": True,
        "sleeves": state.get("sleeves"),
        "reason": state.get("reason"),
    }


@router.get("/signals/opportunity-rail")
def opportunity_rail():
    from src.services.opportunity_rail import build_opportunity_rail

    return build_opportunity_rail()


@router.get("/portfolio/backtest")
def portfolio_backtest(db: Session = Depends(get_db)):
    from src.services.portfolio_backtest import run_portfolio_backtest

    return run_portfolio_backtest(db)


@router.get("/board/layouts")
def list_board_layouts(db: Session = Depends(get_db)):
    from src.services.board_layout import BoardLayoutService

    return {"layouts": BoardLayoutService(db).list_presets()}


@router.get("/board/layout/active")
def active_board_layout(db: Session = Depends(get_db)):
    from src.services.board_layout import BoardLayoutService

    return BoardLayoutService(db).get_active()


@router.post("/board/layout/{preset}")
def set_board_layout(preset: str, db: Session = Depends(get_db)):
    from src.services.board_layout import DEFAULT_PRESETS, BoardLayoutService

    name = preset.strip().lower()
    if name not in DEFAULT_PRESETS:
        raise HTTPException(404, f"Unknown layout preset: {preset}")
    svc = BoardLayoutService(db)
    row = svc.save_preset(name, DEFAULT_PRESETS[name], is_default=True)
    return row


@router.get("/stream/quotes")
async def stream_quotes(symbols: str | None = None):
    """SSE Core14 quote stream — batch from Profit bridge + heartbeat (A2.8 / 7.0)."""
    import asyncio
    import json
    import time

    from src.services.filipe_universe import symbol_list

    settings = get_settings()

    async def generate():
        client = get_profit_client()
        from src.services.resource_profile import get_resource_profile

        poll_sec = get_resource_profile(settings).sse_poll_sec
        if settings.golden_path_mode and not symbols:
            syms = [settings.golden_path_symbol]
        elif symbols:
            syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        else:
            syms = symbol_list()
        heartbeat_sec = settings.quotes_heartbeat_sec
        last_heartbeat = time.monotonic()
        while True:
            batch = await asyncio.to_thread(client.get_quotes_batch, syms)
            payload = {
                "type": "quotes",
                "ts": time.time(),
                "quotes": {
                    s: {
                        "last": q.last,
                        "bid": q.bid,
                        "ask": q.ask,
                        "volume": q.volume,
                    }
                    for s, q in batch.items()
                },
            }
            yield f"data: {json.dumps(payload)}\n\n"

            now = time.monotonic()
            if now - last_heartbeat >= heartbeat_sec:
                yield f"data: {json.dumps({'type': 'heartbeat', 'ts': time.time()})}\n\n"
                last_heartbeat = now

            await asyncio.sleep(poll_sec)

    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/exports/scan")
def scan_exports(db: Session = Depends(get_db)):
    from src.services.profit_export_watcher import scan_profit_exports

    return scan_profit_exports(db)


@router.get("/setup/status")
def setup_status():
    """Integration wizard — what is connected vs what Filipe must provide."""
    from src.services.setup_wizard import build_setup_status

    return build_setup_status()


@router.post("/setup/test")
def setup_test():
    """Run connector probes (Profit sample quote, Clear account, BOVA chain)."""
    from src.services.setup_wizard import run_setup_tests

    return run_setup_tests()


@router.get("/integrations/profit/account")
def profit_account_profile():
    """Active ProfitChart account mapping (no password returned)."""
    from src.services.profit_accounts import profit_account_checklist, resolve_profit_account

    settings = get_settings()
    acct = resolve_profit_account(settings)
    return {
        "active": acct,
        "accounts": profit_account_checklist(settings),
        "password_configured": bool(settings.profit_password.strip()),
        "paper_trading_mode": settings.paper_trading_mode,
        "profit_live_style": settings.profit_live_style,
    }


@router.get("/integrations/profit/test")
def test_profit_bridge():
    client = get_profit_client()
    settings = get_settings()
    sample = client.get_quote("PETR4")
    sample2 = client.get_quote("GGBR4")
    trades = client.get_trades_today()
    chain = client.get_bova_option_chain()
    return {
        "available": client.is_available(),
        "enabled": settings.profit_bridge_enabled,
        "auto_detect": settings.profit_bridge_auto_detect,
        "url": settings.profit_bridge_url,
        "trades_today": len(trades),
        "bova_chain": {
            "underlying": chain.get("underlying"),
            "strikes": len(chain.get("calls", [])) + len(chain.get("puts", [])),
        },
        "sample_quotes": [
            {"symbol": q.symbol, "last": q.last, "volume": q.volume}
            for q in (sample, sample2)
            if q
        ],
    }


@router.get("/integrations/clear/test")
def test_clear_api():
    client = get_clear_client()
    summary = client.get_account_summary()
    return {
        "configured": client.is_configured(),
        "mock_mode": not client.is_configured(),
        "account_id": summary.get("account_id"),
        "balance_brl": summary.get("balance_brl"),
        "day_pnl": summary.get("day_pnl"),
    }


@router.get("/backtests", response_model=list[BacktestRunResponse])
def list_backtests(
    limit: int = 50,
    strategy_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(BacktestRun).order_by(BacktestRun.created_at.desc())
    if strategy_id is not None:
        query = query.filter(BacktestRun.strategy_id == strategy_id)
    return query.limit(limit).all()


@router.get("/optimizations", response_model=list[OptimizationRunResponse])
def list_optimizations(
    limit: int = 50,
    strategy_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(OptimizationRun).order_by(OptimizationRun.created_at.desc())
    if strategy_id is not None:
        query = query.filter(OptimizationRun.strategy_id == strategy_id)
    return query.limit(limit).all()


@router.post("/optimizations/{run_id}/apply", response_model=StrategyResponse)
def apply_optimization(run_id: int, db: Session = Depends(get_db)):
    """Apply best_parameters from an optimization run to its strategy."""
    run = db.get(OptimizationRun, run_id)
    if not run:
        raise HTTPException(404, "Optimization run not found")
    if not run.best_parameters:
        raise HTTPException(400, "No best parameters on this run")
    strategy = db.get(Strategy, run.strategy_id)
    if not strategy:
        raise HTTPException(404, "Strategy not found")
    strategy.parameters = {**(strategy.parameters or {}), **run.best_parameters}
    db.commit()
    db.refresh(strategy)
    return strategy


@router.get("/system/events", response_model=list[SystemEventResponse])
def list_system_events(limit: int = 30, db: Session = Depends(get_db)):
    return (
        db.query(SystemEvent)
        .order_by(SystemEvent.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )


def _normalize_genetic_space(space: dict) -> dict:
    """Accept [min, max] lists from dashboard for genetic search."""
    out: dict = {}
    for key, value in space.items():
        if isinstance(value, list) and len(value) == 2:
            out[key] = (float(value[0]), float(value[1]))
        else:
            out[key] = value
    return out


@router.post("/backtest")
def run_backtest(payload: BacktestRequest, db: Session = Depends(get_db)):
    strategy = db.get(Strategy, payload.strategy_id)
    if not strategy:
        raise HTTPException(404, "Strategy not found")
    svc = BacktestService(db)
    if payload.engine == "profit":
        path = Path(payload.profit_csv_path) if payload.profit_csv_path else None
        run = svc.run_profit_backtest(strategy, payload.symbol, path)
        if run.metrics and run.metrics.get("error"):
            raise HTTPException(400, run.metrics.get("message", run.metrics["error"]))
        return {"run_id": run.id, "metrics": run.metrics}
    if payload.engine == "compare":
        path = Path(payload.profit_csv_path) if payload.profit_csv_path else None
        result = svc.compare_engines(strategy, payload.symbol, path)
        if result.get("profit", {}).get("error"):
            raise HTTPException(400, result["profit"].get("message", "Profit CSV parse failed"))
        return result
    run = svc.run_python_backtest(strategy, payload.symbol)
    return {"run_id": run.id, "metrics": run.metrics}


@router.post("/backtest/upload")
async def upload_profit_csv(file: UploadFile = File(...)):
    """Upload ProfitChart backtest CSV; returns saved path and parsed preview."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files are accepted")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10MB)")
    settings = get_settings()
    path = save_uploaded_csv(content, file.filename, settings.profit_export_path)
    try:
        preview = parse_profit_backtest_csv(path).to_dict()
    except Exception as exc:
        raise HTTPException(400, f"CSV saved but parse failed: {exc}") from exc
    return {"path": str(path), "preview": preview}


@router.post("/optimize")
def run_optimize(payload: OptimizeRequest, db: Session = Depends(get_db)):
    strategy = db.get(Strategy, payload.strategy_id)
    if not strategy:
        raise HTTPException(404, "Strategy not found")
    svc = OptimizerService(db)
    if payload.method == "walk_forward":
        run = WalkForwardOptimizer(db).run(
            strategy, payload.symbol, payload.parameter_space, folds=payload.folds
        )
    elif payload.method == "genetic":
        space = _normalize_genetic_space(payload.parameter_space)
        run = svc.run_genetic_search(strategy, payload.symbol, space)
    else:
        run = svc.run_grid_search(strategy, payload.symbol, payload.parameter_space)
    return {
        "run_id": run.id,
        "method": run.method,
        "status": run.status,
        "best_parameters": run.best_parameters,
        "best_metrics": run.best_metrics,
        "results": run.results,
    }


@router.post("/ollama/chat")
def ollama_chat(payload: OllamaChatRequest):
    reply = get_ollama_client().chat(payload.message, payload.context)
    return {"reply": reply}


@router.get("/account/summary")
def account_summary():
    return get_clear_client().get_account_summary()


@router.get("/risk/cockpit")
def risk_cockpit(db: Session = Depends(get_db)):
    return build_risk_cockpit(db)


@router.get("/risk/summary", response_model=RiskSummaryResponse)
def risk_summary(db: Session = Depends(get_db)):
    return build_risk_summary(db)


@router.get("/risk/profile", response_model=RiskProfileResponse)
def get_risk_profile(db: Session = Depends(get_db)):
    profile = get_or_create_profile(db)
    return profile_to_dict(profile)


@router.put("/risk/profile", response_model=RiskProfileResponse)
def put_risk_profile(payload: RiskProfileUpdate, db: Session = Depends(get_db)):
    profile = update_profile(db, payload.model_dump(exclude_unset=True))
    return profile_to_dict(profile)


@router.get("/profit/pnl", response_model=ProfitPnlResponse)
def profit_pnl(db: Session = Depends(get_db)):
    return resolve_day_pnl(db)


@router.get("/market/clocks")
def market_clocks():
    from src.services.market_clocks import get_market_clocks

    return get_market_clocks()


@router.get("/watchlist/enriched")
def watchlist_enriched(db: Session = Depends(get_db)):
    from src.services.enriched_watchlist import build_enriched_watchlist

    return build_enriched_watchlist(db)


@router.get("/universe/futures")
def universe_futures():
    from src.services.futures_quotes import build_futures_watchlist_rows
    from src.services.futures_universe import load_futures_universe

    return {
        "symbols": [f.to_dict() for f in load_futures_universe()],
        "quotes": build_futures_watchlist_rows(),
    }


@router.get("/signals/social")
def social_signals(limit: int = 12):
    from src.config import get_settings
    from src.services.social_signals import get_social_signals

    if not get_settings().social_signals_runtime_enabled:
        return {
            "signals": [],
            "count": 0,
            "read_only": True,
            "auto_trade": False,
            "disclaimer": "Social signals disabled",
            "sources": [],
        }
    return get_social_signals(limit=limit)


@router.get("/universe/crypto")
def universe_crypto():
    from src.services.crypto_quotes import build_crypto_watchlist_rows
    from src.services.crypto_universe import load_crypto_universe

    return {
        "symbols": [c.to_dict() for c in load_crypto_universe()],
        "quotes": build_crypto_watchlist_rows(),
        "read_only": True,
        "auto_trade": False,
    }


@router.get("/archaeology/timeline")
def archaeology_timeline(
    limit: int = 100,
    symbol: str | None = None,
    db: Session = Depends(get_db),
):
    from src.services.trade_archaeology import build_timeline

    return build_timeline(db, limit=limit, symbol=symbol)


@router.post("/archaeology/import")
async def archaeology_import(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload Profit trade-history CSV for archaeology timeline."""
    from src.config import get_settings
    from src.services.trade_archaeology import import_trade_csv

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files are accepted")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10MB)")
    settings = get_settings()
    path = save_uploaded_csv(content, file.filename, settings.archaeology_import_path)
    try:
        return import_trade_csv(db, path)
    except Exception as exc:
        raise HTTPException(400, f"CSV saved but import failed: {exc}") from exc


@router.post("/archaeology/import/excel")
async def archaeology_import_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload B3 trade history Excel (.xlsx) — full Filipe history import."""
    import re

    from src.config import get_settings
    from src.services.b3_history_import import import_b3_history_excel

    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Only .xlsx or .xls files are accepted")
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 25MB)")
    settings = get_settings()
    dest_dir = settings.archaeology_import_path
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w.\-]", "_", file.filename) or "history.xlsx"
    dest = dest_dir / safe
    dest.write_bytes(content)
    try:
        return import_b3_history_excel(db, dest)
    except Exception as exc:
        raise HTTPException(400, f"Excel import failed: {exc}") from exc


@router.post("/archaeology/scan")
def archaeology_scan(db: Session = Depends(get_db)):
    from src.services.trade_archaeology import scan_archaeology_dir

    return scan_archaeology_dir(db)


@router.get("/archaeology/symbol/{symbol}/insights")
def archaeology_symbol_insights(symbol: str, db: Session = Depends(get_db)):
    from src.services.archaeology_backtest import archaeology_symbol_insights as build_insights

    return build_insights(db, symbol)


@router.get("/archaeology/summary")
def archaeology_summary(limit: int = 15, db: Session = Depends(get_db)):
    from src.services.archaeology_backtest import build_archaeology_summary

    return build_archaeology_summary(db, limit=min(limit, 50))


@router.post("/cei/parse")
async def cei_parse_upload(file: UploadFile = File(...)):
    """Upload CEI/B3 trade export for parser spike preview."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files are accepted")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10MB)")
    from src.config import get_settings
    from src.services.cei_parser import parse_cei_export

    settings = get_settings()
    path = save_uploaded_csv(content, file.filename, settings.archaeology_import_path)
    try:
        return parse_cei_export(path)
    except Exception as exc:
        raise HTTPException(400, f"CEI parse failed: {exc}") from exc


@router.post("/cei/import")
async def cei_import_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import CEI/B3 trade CSV into archaeology timeline (same row pipeline as Profit)."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files are accepted")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10MB)")
    from src.config import get_settings
    from src.services.trade_archaeology import import_trade_csv

    settings = get_settings()
    path = save_uploaded_csv(content, file.filename, settings.archaeology_import_path)
    try:
        result = import_trade_csv(db, path)
        result["source_format"] = "cei"
        return result
    except Exception as exc:
        raise HTTPException(400, f"CEI import failed: {exc}") from exc


@router.get("/symbols/{symbol}/trade-product")
def symbol_trade_product(symbol: str, db: Session = Depends(get_db)):
    from src.services.board_notes import BoardNotesService
    from src.services.trade_product import build_trade_product

    sym = symbol.strip().upper()
    svc = TradeIdeaService(db)
    ideas = svc.list_ideas(limit=5, symbol=sym)
    if not ideas:
        raise HTTPException(404, f"No ideas for {sym}")
    note_row = BoardNotesService(db).get(sym)
    note = note_row.content if note_row else None
    return build_trade_product(svc.to_dict(ideas[0]), note=note, session=db)


@router.get("/symbols/{symbol}/odds")
def symbol_odds(symbol: str, structure_type: str | None = None, db: Session = Depends(get_db)):
    from src.services.odds_panel import pattern_odds

    return pattern_odds(db, symbol=symbol, structure_type=structure_type)


@router.get("/pulse")
def pulse_rail():
    from src.services.pulse_rail import get_pulse_rail

    return get_pulse_rail()


@router.post("/replay/batch")
def replay_batch_run(
    payload: dict = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    """Run Profit Replay training for Core5 + WIN/WDO symbols (13.0-beta)."""
    from src.services.replay_batch import run_replay_batch

    symbols = payload.get("symbols")
    if symbols is not None and not isinstance(symbols, list):
        raise HTTPException(400, "symbols must be a list")
    return run_replay_batch(
        db,
        symbols=symbols,
        auto_promote=bool(payload.get("auto_promote", True)),
        speed=float(payload.get("speed", 10.0)),
    )


@router.get("/journal/desk")
def journal_desk(days: int = 30, db: Session = Depends(get_db)):
    from src.services.trade_journal_desk import build_trade_journal_desk

    return build_trade_journal_desk(db, days=min(max(days, 1), 365))


@router.get("/journal/export.csv")
def journal_export_csv(days: int = 90, db: Session = Depends(get_db)):
    from fastapi.responses import PlainTextResponse

    from src.services.trade_journal_desk import export_journal_csv

    body = export_journal_csv(db, days=min(max(days, 1), 365))
    return PlainTextResponse(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="arbitragem_journal.csv"'},
    )


@router.get("/phase-c/status")
def phase_c_status(db: Session = Depends(get_db)):
    from src.services.phase_c_gate import evaluate_phase_c_gate

    return evaluate_phase_c_gate(db)


@router.post("/replay/run")
def replay_run(payload: ReplayRunRequest, db: Session = Depends(get_db)):
    from src.services.replay_engine import start_replay

    return start_replay(
        strategy=payload.strategy,
        symbol=payload.symbol,
        speed=payload.speed,
        mode=payload.mode,
        session=db,
    )


@router.get("/replay/sessions")
def replay_sessions(limit: int = 20, db: Session = Depends(get_db)):
    from src.services.replay_engine import list_recent_sessions

    return {"sessions": list_recent_sessions(db, limit=min(limit, 50))}


@router.get("/replay/{job_id}")
def replay_session_detail(job_id: str, db: Session = Depends(get_db)):
    from src.services.replay_engine import get_replay

    row = get_replay(job_id, session=db)
    if not row:
        raise HTTPException(404, "Replay session not found")
    return row


@router.post("/replay/training/run")
def replay_training_run(db: Session = Depends(get_db)):
    from src.services.replay_engine import run_training_cycle

    return run_training_cycle(db)


@router.get("/engine/mind")
def engine_mind_status():
    from src.autonomous.engine_mind import get_engine_mind

    return get_engine_mind().snapshot()


@router.get("/knowledge/status")
def knowledge_status_api():
    from src.services.knowledge.store import knowledge_status

    return knowledge_status()


@router.get("/knowledge/search")
def knowledge_search_api(q: str, symbol: str | None = None, tags: str | None = None, limit: int = 8):
    from src.services.knowledge.store import search_chunks

    return {"query": q, "results": search_chunks(q, symbol=symbol, tags=tags, limit=limit)}


@router.post("/knowledge/ingest/replays")
def knowledge_ingest_replays(limit: int = 20, db: Session = Depends(get_db)):
    from src.services.knowledge.replay_ingest import ingest_recent_replays

    return ingest_recent_replays(db, limit=min(limit, 50))


@router.post("/knowledge/ingest/strategies")
def knowledge_ingest_strategies(limit: int = 50, db: Session = Depends(get_db)):
    from src.services.knowledge.replay_ingest import ingest_all_stored_strategies

    return ingest_all_stored_strategies(db, limit=min(limit, 100))


@router.get("/self-healing/breakers")
def self_healing_breakers():
    from src.services.self_healing import all_breakers_snapshot

    return {"breakers": all_breakers_snapshot()}


@router.get("/self-healing/health")
def self_healing_health():
    from src.services.self_healing.health_registry import health_snapshot

    return health_snapshot()


@router.post("/ideas/{idea_id}/brief")
def idea_decision_brief(idea_id: int, db: Session = Depends(get_db)):
    from src.services.decision_brief import build_decision_brief

    try:
        return build_decision_brief(db, idea_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/ideas/{idea_id}/theory-cards")
def idea_theory_cards(idea_id: int, db: Session = Depends(get_db)):
    from src.models import TradeIdea
    from src.services.theory_cards import build_theory_cards

    idea = db.get(TradeIdea, idea_id)
    if not idea:
        raise HTTPException(404, "Idea not found")
    meta = idea.meta or {}
    cards = meta.get("theory_cards") or build_theory_cards(
        symbol=idea.symbol, structure_type=idea.structure_type, tags=idea.rationale_tags
    )
    return {"idea_id": idea_id, "cards": cards, "count": len(cards)}


@router.get("/autonomous/outcomes")
def autonomous_outcomes(symbol: str | None = None, db: Session = Depends(get_db)):
    from src.services.outcome_ranker import rank_outcomes

    return {"outcomes": rank_outcomes(db, symbol=symbol)}


@router.get("/autonomous/patches")
def autonomous_patches_list(status: str = "pending", db: Session = Depends(get_db)):
    from src.services.patch_proposals import list_proposals

    return {"proposals": list_proposals(db, status=status or None)}


@router.post("/autonomous/patches/generate")
def autonomous_patches_generate(symbol: str | None = None, db: Session = Depends(get_db)):
    from src.services.patch_proposals import generate_patch_proposals

    return {"created": generate_patch_proposals(db, symbol=symbol)}


@router.post("/autonomous/patches/{proposal_id}/approve")
def autonomous_patch_approve(proposal_id: int, db: Session = Depends(get_db)):
    from src.services.patch_proposals import approve_proposal

    try:
        return approve_proposal(db, proposal_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/autonomous/patches/{proposal_id}/reject")
def autonomous_patch_reject(
    proposal_id: int,
    reason: str = "",
    db: Session = Depends(get_db),
):
    from src.services.patch_proposals import reject_proposal

    try:
        return reject_proposal(db, proposal_id, reason=reason)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/symbols/{symbol}/graduation")
def symbol_graduation(symbol: str, db: Session = Depends(get_db)):
    from src.services.paper_graduation import graduation_status

    return graduation_status(db, symbol)


@router.get("/motor/universe")
def motor_universe(db: Session = Depends(get_db)):
    from src.services.motor_universe import motor_universe_policy

    return motor_universe_policy(db)


@router.get("/knowledge/distill")
def knowledge_distill():
    from src.services.rule_distillation import distill_candidate_axioms

    return distill_candidate_axioms()


@router.get("/daily-briefing")
def daily_briefing_api(db: Session = Depends(get_db)):
    from src.services.daily_briefing import build_daily_briefing

    return build_daily_briefing(db)


@router.post("/strategy-store/scan")
def strategy_store_scan(db: Session = Depends(get_db)):
    from src.services.strategy_store import scan_strategy_directories

    return scan_strategy_directories(db)


@router.get("/strategy-store")
def strategy_store_list(limit: int = 50, db: Session = Depends(get_db)):
    from src.services.strategy_store import list_stored_strategies

    return {"strategies": list_stored_strategies(db, limit=min(limit, 100))}


@router.get("/strategy-store/{stored_id}")
def strategy_store_detail(stored_id: int, db: Session = Depends(get_db)):
    from src.services.strategy_store import get_stored_strategy

    row = get_stored_strategy(db, stored_id)
    if not row:
        raise HTTPException(404, "Stored strategy not found")
    return row


@router.get("/kpi/history")
def kpi_history(range: str = "today", db: Session = Depends(get_db)):
    from src.services.kpi_history import build_kpi_history

    allowed = {"today", "5d", "20d", "3mo", "ytd"}
    key = range if range in allowed else "today"
    return build_kpi_history(db, key)


@router.get("/education")
def education_pack():
    from src.services.education import get_education_pack

    return get_education_pack()


@router.get("/education/axioms")
def education_axioms():
    from src.services.education import list_axioms

    return {"axioms": list_axioms()}


@router.get("/education/structures")
def education_structures():
    from src.services.education import list_structures

    return {"structures": list_structures()}


@router.get("/education/daily")
def education_daily():
    from src.services.education import daily_axiom

    return daily_axiom()


@router.get("/education/structures/{structure_type}")
def education_structure_blurb(structure_type: str):
    from src.services.education import structure_blurb

    blurb = structure_blurb(structure_type)
    if not blurb:
        raise HTTPException(404, f"No education blurb for {structure_type}")
    return {"structure_type": structure_type.lower(), **blurb}


@router.get("/paper/validation")
def paper_validation_checklist(db: Session = Depends(get_db)):
    from src.services.paper_validation import build_paper_validation

    return build_paper_validation(db)


@router.get("/paper/journal/export")
def paper_journal_export(
    format: str = "json",
    db: Session = Depends(get_db),
):
    from fastapi.responses import PlainTextResponse

    from src.services.paper_validation import (
        build_journal_export,
        journal_csv_text,
        write_journal_csv,
    )

    fmt = format.lower()
    if fmt == "csv":
        return PlainTextResponse(
            content=journal_csv_text(db),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="paper_journal.csv"'},
        )
    if fmt == "file":
        return write_journal_csv(db)
    return build_journal_export(db)


@router.post("/paper/journal/export")
def paper_journal_export_file(db: Session = Depends(get_db)):
    from src.services.paper_validation import write_journal_csv

    return write_journal_csv(db)


@router.get("/paper/crypto/preview")
def paper_crypto_preview(
    symbol: str,
    side: str = "buy",
    quantity: float = 0.01,
):
    from src.services.crypto_paper import preview_crypto_fill

    try:
        return preview_crypto_fill(symbol=symbol, side=side, quantity=quantity)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/paper/crypto/execute")
def paper_crypto_execute(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    from src.services.crypto_paper import execute_crypto_paper

    symbol = str(payload.get("symbol", "")).strip()
    side = str(payload.get("side", "buy"))
    try:
        quantity = float(payload.get("quantity", 0))
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "quantity must be a number") from exc
    note = payload.get("note")
    try:
        return execute_crypto_paper(
            db,
            symbol=symbol,
            side=side,
            quantity=quantity,
            note=str(note) if note else None,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/ntsl/arm")
def ntsl_arm(payload: NtslArmRequest, db: Session = Depends(get_db)):
    from src.integrations.profit_bridge import get_profit_client
    from src.services.ntsl_arm import arm_ntsl
    from src.services.trade_ideas import TradeIdeaService

    legs = payload.legs
    if not legs:
        svc = TradeIdeaService(db)
        quote = get_profit_client().get_quote(payload.symbol)
        legs = svc._legs_for_structure(
            payload.structure_type, payload.symbol, payload.side, quote
        )

    return arm_ntsl(
        symbol=payload.symbol,
        structure_type=payload.structure_type,
        side=payload.side,
        legs=legs,
        ntsl_code=payload.ntsl_code,
        stop_ticks=payload.stop_ticks,
        target_ticks=payload.target_ticks,
    )


@router.post("/autonomous/run")
def autonomous_run(db: Session = Depends(get_db)):
    """Run one autonomous daily routine (scan + WFO + rankings sync)."""
    from src.autonomous.engine import AutonomousEngine

    return AutonomousEngine(db).run_daily_routine_sync().to_dict()


from src.web.api.v1.backtest import router as backtest_rankings_router

router.include_router(backtest_rankings_router, prefix="/backtest", tags=["backtest"])


@router.get("/golden-path")
def golden_path_status(db: Session = Depends(get_db)):
    from src.services.golden_path import evaluate_golden_path

    return evaluate_golden_path(db)


@router.get("/golden-path/reconcile")
def golden_path_reconcile(db: Session = Depends(get_db)):
    from src.services.pnl_reconcile import reconcile_symbol_pnl

    settings = get_settings()
    return reconcile_symbol_pnl(db, settings.golden_path_symbol)


@router.get("/ops/memory")
def ops_memory():
    from src.services.ops_panel import build_ops_panel

    return build_ops_panel()


@router.get("/ops/live-radar")
def ops_live_radar(db: Session = Depends(get_db)):
    """Stack health lamps — API, bridge, motor, scanner, mind, sleeves."""
    from src.services.live_radar import build_live_radar

    return build_live_radar(db)


@router.get("/symbol-factory/status")
def symbol_factory_status(db: Session = Depends(get_db)):
    from src.services.symbol_factory import factory_status

    return factory_status(db)


@router.post("/symbol-factory/shadow")
def symbol_factory_add_shadow(payload: dict = Body(...), db: Session = Depends(get_db)):
    from src.services.symbol_factory import add_shadow_symbol

    symbol = str(payload.get("symbol", "")).strip()
    if not symbol:
        raise HTTPException(400, "symbol required")
    result = add_shadow_symbol(db, symbol)
    if not result.get("ok"):
        raise HTTPException(409, detail=result)
    return result


@router.post("/symbol-factory/promote")
def symbol_factory_promote(payload: dict = Body(...), db: Session = Depends(get_db)):
    from src.services.symbol_factory import promote_shadow_symbol

    symbol = str(payload.get("symbol", "")).strip()
    if not symbol:
        raise HTTPException(400, "symbol required")
    result = promote_shadow_symbol(db, symbol)
    if not result.get("ok"):
        raise HTTPException(409, detail=result)
    return result
