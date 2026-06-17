"""FastAPI application entry point."""

from contextlib import asynccontextmanager

import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src import __version__
from src.api.routes import router
from src.web.deps import WEB_ROOT
from src.web.router import router as web_router
from src.config import get_settings
from src.logging_config import setup_logging
from src.models import init_db
from src.scheduler import start_scheduler, stop_scheduler
from src.services.strategy_manager import StrategyService
from src.models import get_session_factory
from src.web.board_auth import BoardAuthMiddleware


async def _orchestrator_loop() -> None:
    """Trading motor — scan, rank, paper-execute when sleeves ON."""
    from src.services.trading_orchestrator import (
        motor_session_open,
        orchestrator_should_run,
    )
    from src.services.trader_agent import run_trader_cycle

    await asyncio.sleep(8)
    while True:
        settings = get_settings()
        if settings.paper_trading_mode and settings.auto_trading_on_sleeves:
            interval = max(15, settings.effective_paper_orchestrator_interval_sec)
        else:
            interval = max(20, settings.effective_orchestrator_interval_sec)
        if orchestrator_should_run() and motor_session_open():
            session = get_session_factory()()
            try:
                await asyncio.to_thread(run_trader_cycle, session)
            except Exception:
                pass
            finally:
                session.close()
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_db()
    session = get_session_factory()()
    try:
        StrategyService(session).get_or_create_sample()
    finally:
        session.close()
    start_scheduler()
    settings = get_settings()
    motor_task = None
    if settings.autonomy_enabled or (
        settings.paper_trading_mode and settings.auto_trading_on_sleeves
    ):
        motor_task = asyncio.create_task(_orchestrator_loop())
    yield
    if motor_task:
        motor_task.cancel()
        try:
            await motor_task
        except asyncio.CancelledError:
            pass
    stop_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Arbitragem Dashboard API",
        version=__version__,
        description="B3 options scalping — ProfitChart + Clear + Ollama",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(BoardAuthMiddleware)
    app.include_router(router, prefix="/api/v1")
    app.include_router(web_router)
    app.mount("/static", StaticFiles(directory=str(WEB_ROOT / "static")), name="static")
    return app


app = create_app()
