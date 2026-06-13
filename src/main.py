"""FastAPI application entry point."""

from contextlib import asynccontextmanager

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
    yield
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
    app.include_router(router, prefix="/api/v1")
    app.include_router(web_router)
    app.mount("/static", StaticFiles(directory=str(WEB_ROOT / "static")), name="static")
    return app


app = create_app()
