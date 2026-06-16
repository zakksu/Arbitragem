"""SQLAlchemy models for trades, strategies, scans, and journal."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from src.config import get_settings


class Base(DeclarativeBase):
    pass


class StrategyStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class StructureType(str, Enum):
    """Multi-leg structure template (3.0)."""

    SCALP = "scalp"
    COVERED_CALL = "covered_call"
    VERTICAL = "vertical"
    COLLAR = "collar"
    BOVA_HEDGE = "bova_hedge"
    PAIR_SPREAD = "pair_spread"


class LegType(str, Enum):
    """Per-leg asset class for NTSL export and risk."""

    CASH = "cash"
    CALL = "call"
    PUT = "put"
    BOVA_CALL = "bova_call"
    BOVA_PUT = "bova_put"


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ntsl_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=StrategyStatus.DRAFT.value)
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    daily_loss_limit_brl: Mapped[float] = mapped_column(Float, default=500.0)
    max_contracts: Mapped[int] = mapped_column(Integer, default=10)
    max_open_positions: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    trades: Mapped[list["Trade"]] = relationship(back_populates="strategy")
    backtest_runs: Mapped[list["BacktestRun"]] = relationship(back_populates="strategy")
    optimization_runs: Mapped[list["OptimizationRun"]] = relationship(back_populates="strategy")


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.id"), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="clear")  # clear | profit
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(10))
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    journal_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    strategy: Mapped["Strategy | None"] = relationship(back_populates="trades")


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.id"), nullable=True)
    engine: Mapped[str] = mapped_column(String(20))  # profit | python
    symbol: Mapped[str] = mapped_column(String(32))
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    profit_export_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    strategy: Mapped["Strategy | None"] = relationship(back_populates="backtest_runs")


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.id"), nullable=True)
    method: Mapped[str] = mapped_column(String(30))  # grid | genetic | walk_forward
    status: Mapped[str] = mapped_column(String(20), default="pending")
    parameter_space: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    best_parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    best_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    strategy: Mapped["Strategy | None"] = relationship(back_populates="optimization_runs")


class ScanResult(Base):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    open_interest: Mapped[int | None] = mapped_column(Integer, nullable=True)
    iv_skew: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    spike_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    pattern_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    alert_level: Mapped[str] = mapped_column(String(20), default="info")
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    mood: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SystemEvent(Base):
    __tablename__ = "system_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(20))
    component: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BoardNote(Base):
    """Per-symbol blackboard notes and price levels."""

    __tablename__ = "board_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    levels: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TradeIdea(Base):
    """Structured scalp / options idea for Idea Stack (2.0)."""

    __tablename__ = "trade_ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    structure_type: Mapped[str] = mapped_column(String(40), default="scalp")
    side: Mapped[str] = mapped_column(String(10), default="neutral")
    status: Mapped[str] = mapped_column(String(20), default="detected", index=True)
    reliability: Mapped[float] = mapped_column(Float, default=0.0)
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_ticks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_ticks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    legs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    backtest_proof: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scan_result_id: Mapped[int | None] = mapped_column(ForeignKey("scan_results.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RiskProfile(Base):
    """Persisted risk limits — one row per env (4.0-alpha)."""

    __tablename__ = "risk_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    max_daily_loss_brl: Mapped[float] = mapped_column(Float, default=500.0)
    max_open_positions: Mapped[int] = mapped_column(Integer, default=5)
    cost_per_trade_brl: Mapped[float] = mapped_column(Float, default=50.0)
    max_net_delta: Mapped[float] = mapped_column(Float, default=0.5)
    sector_caps: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class BoardLayout(Base):
    """Saved blackboard column layout presets (3.0-rc)."""

    __tablename__ = "board_layouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    preset: Mapped[str] = mapped_column(String(40), default="scalp")
    columns: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_engine():
    settings = get_settings()
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(settings.database_url, connect_args=connect_args)


def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


def init_db() -> None:
    from sqlalchemy import event, inspect, text

    from src.config import PROJECT_ROOT

    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    # Migration-safe column adds for existing SQLite DBs (2.0 → 3.0)
    if str(get_settings().database_url).startswith("sqlite"):
        insp = inspect(engine)
        if "trade_ideas" in insp.get_table_names():
            existing = {c["name"] for c in insp.get_columns("trade_ideas")}
            alters: list[str] = []
            if "legs" not in existing:
                alters.append("ALTER TABLE trade_ideas ADD COLUMN legs JSON")
            if "structure_type" not in existing:
                alters.append(
                    "ALTER TABLE trade_ideas ADD COLUMN structure_type VARCHAR(40) DEFAULT 'scalp'"
                )
            with engine.connect() as conn:
                for stmt in alters:
                    conn.execute(text(stmt))
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.commit()
        else:
            with engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.commit()

    from src.services.board_layout import BoardLayoutService
    from src.services.risk_profile import get_or_create_profile

    session = get_session_factory()()
    try:
        BoardLayoutService(session).seed_defaults()
        get_or_create_profile(session)
    finally:
        session.close()
