"""Pydantic schemas for API request/response."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StrategyCreate(BaseModel):
    name: str
    description: str | None = None
    ntsl_code: str | None = None
    parameters: dict[str, Any] | None = None
    daily_loss_limit_brl: float = 500.0
    max_contracts: int = 10
    max_open_positions: int = 3


class StrategyRiskUpdate(BaseModel):
    daily_loss_limit_brl: float | None = None
    max_contracts: int | None = None
    max_open_positions: int | None = None
    parameters: dict[str, Any] | None = None


class StrategyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    ntsl_code: str | None = None
    parameters: dict[str, Any] | None = None
    daily_loss_limit_brl: float | None = None
    max_contracts: int | None = None
    max_open_positions: int | None = None


class StrategyResponse(BaseModel):
    id: int
    name: str
    description: str | None
    ntsl_code: str | None = None
    status: str
    parameters: dict[str, Any] | None
    daily_loss_limit_brl: float
    max_contracts: int
    max_open_positions: int

    model_config = {"from_attributes": True}


class TradeResponse(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: int
    price: float
    fees: float = 0.0
    pnl: float | None
    source: str = "clear"
    executed_at: datetime
    ai_analysis: str | None

    model_config = {"from_attributes": True}


class BacktestRequest(BaseModel):
    strategy_id: int
    symbol: str = "BOVAX125"
    engine: str = Field(default="python", pattern="^(python|profit|compare)$")
    profit_csv_path: str | None = None


class ProfitBacktestRunRequest(BaseModel):
    symbol: str = "PETR4"
    strategy: str = "scalp_default"
    period: str = "90d"


class StructureIdeaRequest(BaseModel):
    symbol: str = "PETR4"
    structure_type: str = "covered_call"
    side: str = "long"


class OptimizeRequest(BaseModel):
    strategy_id: int
    symbol: str = "BOVAX125"
    method: str = Field(default="grid", pattern="^(grid|genetic|walk_forward)$")
    folds: int = Field(default=3, ge=2, le=10)
    parameter_space: dict[str, Any]


class OllamaChatRequest(BaseModel):
    message: str
    context: str | None = None


class ScanResultResponse(BaseModel):
    id: int
    scan_date: datetime
    symbol: str
    volume: int | None
    open_interest: int | None
    iv_skew: float | None
    price_change_pct: float | None
    spike_score: float | None
    pattern_tags: list[str] | None
    alert_level: str
    raw_data: dict[str, Any] | None
    ai_summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str
    version: str
    ollama: bool
    profit_bridge: bool
    clear_api: bool
    alerts_enabled: bool = False
    alerts_configured: bool = False
    paper_trading_mode: bool = True
    scanner_mode: str = "ibov_top20"
    scanner_symbol_count: int = 0


class BacktestRunResponse(BaseModel):
    id: int
    strategy_id: int | None
    engine: str
    symbol: str
    metrics: dict[str, Any] | None
    profit_export_path: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OptimizationRunResponse(BaseModel):
    id: int
    strategy_id: int | None
    method: str
    status: str
    best_parameters: dict[str, Any] | None
    best_metrics: dict[str, Any] | None
    results: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class AlertsStatusResponse(BaseModel):
    enabled: bool
    configured: bool
    telegram: bool
    discord: bool


class SystemEventResponse(BaseModel):
    id: int
    level: str
    component: str
    message: str
    details: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RiskSummaryResponse(BaseModel):
    paper_trading_mode: bool
    day_pnl: float
    broker_day_pnl: float
    journal_pnl: float
    profit_day_pnl: float | None = None
    pnl_source: str = "clear"
    trades_today: int
    active_strategies: int
    total_strategies: int
    default_loss_limit_brl: float
    tightest_loss_limit_brl: float
    loss_limit_used_pct: float
    max_contracts_default: int
    status: str
    can_start_new_strategy: bool
    kill_switch_active: bool = False
    kill_switch_reason: str | None = None
    sleeves: dict[str, bool] | None = None
    sleeves_all_open: bool = True
    sleeves_reason: str | None = None
    autonomy_enabled: bool = False
    can_confirm_ideas: bool = True
    can_execute_ideas: bool = True


class RiskProfileResponse(BaseModel):
    max_daily_loss_brl: float
    max_open_positions: int
    cost_per_trade_brl: float
    max_net_delta: float
    sector_caps: dict[str, float]
    updated_at: str | None = None


class RiskProfileUpdate(BaseModel):
    max_daily_loss_brl: float | None = None
    max_open_positions: int | None = None
    cost_per_trade_brl: float | None = None
    max_net_delta: float | None = None
    sector_caps: dict[str, float] | None = None


class ProfitPnlResponse(BaseModel):
    day_pnl: float
    journal_pnl: float
    profit_day_pnl: float | None = None
    broker_day_pnl: float
    pnl_source: str
    trades_today: int


class ReplayRunRequest(BaseModel):
    strategy: str = "scalp_default"
    symbol: str = "PETR4"
    speed: float = 10.0
    mode: str = "sandbox"


class NtslArmRequest(BaseModel):
    symbol: str
    structure_type: str = "scalp"
    side: str = "long"
    ntsl_code: str | None = None
    legs: list[dict[str, Any]] | None = None
    stop_ticks: int | None = None
    target_ticks: int | None = None


class TradeIdeaResponse(BaseModel):
    id: int
    symbol: str
    structure_type: str
    side: str
    status: str
    reliability: float
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    stop_ticks: int | None = None
    target_ticks: int | None = None
    title: str | None = None
    rationale: str | None = None
    rationale_tags: list[str] | None = None
    legs: list[dict[str, Any]] | None = None
    backtest_proof: dict[str, Any] | None = None
    created_at: datetime | None = None
    confirmed_at: datetime | None = None
    executed_at: datetime | None = None

    model_config = {"from_attributes": True}
