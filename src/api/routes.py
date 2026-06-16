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
        "ollama": get_ollama_client().is_available() if settings.ollama_enabled else False,
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
        ollama_ok = get_ollama_client().is_available() if settings.ollama_enabled else False
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
    try:
        idea = TradeIdeaService(db).confirm_idea(idea_id, paper_override=paper_override)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return TradeIdeaService(db).to_dict(idea)


@router.post("/ideas/{idea_id}/execute")
def execute_trade_idea(idea_id: int, db: Session = Depends(get_db)):
    try:
        idea = TradeIdeaService(db).execute_idea(idea_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return TradeIdeaService(db).to_dict(idea)


@router.get("/symbols/{symbol}/report")
def symbol_report(symbol: str, force: bool = False, db: Session = Depends(get_db)):
    from src.services.symbol_report import build_symbol_report

    return build_symbol_report(db, symbol, force=force)


@router.get("/ideas/{idea_id}")
def get_trade_idea(idea_id: int, db: Session = Depends(get_db)):
    from src.models import TradeIdea

    idea = db.get(TradeIdea, idea_id)
    if not idea:
        raise HTTPException(404, "Idea not found")
    return TradeIdeaService(db).to_dict(idea)


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
    """Toggle kill switch — blocks confirm/execute when active (A2.6c)."""
    from src.models import TradeIdea
    from src.services.kill_switch import set_active
    from src.services.system_audit import log_event

    active = bool(payload.get("active", True))
    reason = str(payload.get("reason") or "Manual kill switch")
    state = set_active(active, reason=reason if active else "")

    rejected = 0
    paused = 0
    if active:
        for s in db.query(Strategy).filter(Strategy.status == "active").all():
            try:
                StrategyService(db).pause_strategy(s.id)
                paused += 1
            except ValueError:
                pass
        for idea in db.query(TradeIdea).filter(
            TradeIdea.status.in_(["detected", "backtested", "confirmed"])
        ).all():
            idea.status = "rejected"
            idea.rationale = (idea.rationale or "") + "\n[Kill switch] Idea cancelled."
            rejected += 1
        log_event(
            db,
            level="warning",
            component="kill_switch",
            message=f"Kill switch ON — paused {paused} strategies, rejected {rejected} ideas",
            details={**state, "paused_strategies": paused, "rejected_ideas": rejected},
        )
        db.commit()
    else:
        log_event(
            db,
            level="info",
            component="kill_switch",
            message="Kill switch OFF — confirms and executes allowed",
            details=state,
        )
        db.commit()

    return {**state, "paused_strategies": paused, "rejected_ideas": rejected}


@router.post("/strategies/pause-all")
def pause_all_strategies(db: Session = Depends(get_db)):
    """Legacy alias — activates kill switch and rejects pending ideas."""
    result = risk_kill_switch({"active": True, "reason": "pause-all"}, db=db)
    return {
        "paused": result.get("paused_strategies", 0),
        "rejected_ideas": result.get("rejected_ideas", 0),
        **result,
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
    """SSE Core14 quote stream — batch from Profit bridge + 15s heartbeat (A2.8)."""
    import asyncio
    import json
    import time

    from src.services.filipe_universe import symbol_list

    async def generate():
        client = get_profit_client()
        syms = (
            [s.strip().upper() for s in symbols.split(",") if s.strip()]
            if symbols
            else symbol_list()
        )
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
            if now - last_heartbeat >= 15:
                yield f"data: {json.dumps({'type': 'heartbeat', 'ts': time.time()})}\n\n"
                last_heartbeat = now

            await asyncio.sleep(2)

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
    from src.services.filipe_universe import load_filipe_core14
    from src.services.risk_profile import get_or_create_profile
    from src.services.watchlist_enrich import enrich_watchlist_rows

    symbols = load_filipe_core14()
    rows = [s.to_dict() for s in symbols] if symbols else []
    sym_list = [r["symbol"] for r in rows if r.get("symbol")]
    client = get_profit_client()
    batch = client.get_quotes_batch(sym_list)
    for row in rows:
        q = batch.get(row["symbol"])
        if q:
            row["last"] = q.last
            row["bid"] = q.bid
            row["ask"] = q.ask
    svc = TradeIdeaService(db)
    ideas = [svc.to_dict(i) for i in svc.list_ideas(limit=50)]
    profile = get_or_create_profile(db)
    enriched = enrich_watchlist_rows(rows, ideas, cost_per_trade_brl=profile.cost_per_trade_brl)
    return {"symbols": enriched, "count": len(enriched)}


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


@router.post("/replay/run")
def replay_run(payload: ReplayRunRequest):
    from src.services.replay_lab import start_replay

    return start_replay(
        strategy=payload.strategy,
        symbol=payload.symbol,
        speed=payload.speed,
        mode=payload.mode,
    )


@router.get("/kpi/history")
def kpi_history(range: str = "today", db: Session = Depends(get_db)):
    from src.services.kpi_history import build_kpi_history

    allowed = {"today", "5d", "20d", "3mo", "ytd"}
    key = range if range in allowed else "today"
    return build_kpi_history(db, key)


@router.post("/ntsl/arm")
def ntsl_arm(payload: NtslArmRequest):
    from src.services.ntsl_arm import arm_ntsl

    return arm_ntsl(
        symbol=payload.symbol,
        structure_type=payload.structure_type,
        side=payload.side,
        ntsl_code=payload.ntsl_code,
    )
