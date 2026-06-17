"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_secret_key: str = "dev-secret-change-me"
    log_level: str = "INFO"
    timezone: str = "America/Sao_Paulo"

    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'arbitragem.db'}"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_base_url: str = "http://localhost:8000"

    streamlit_port: int = 8501

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: int = 120
    ollama_probe_timeout_seconds: float = 1.5
    ollama_enabled: bool = True
    scanner_ollama_on_scan: bool = False

    clear_api_base_url: str = "https://api.clear.com.br/smarttrader"
    clear_api_key: str = ""
    clear_api_secret: str = ""
    clear_account_id: str = ""

    profit_bridge_enabled: bool = False
    profit_bridge_auto_detect: bool = True
    profit_bridge_url: str = "http://localhost:9100"
    profit_dll_path: str = ""
    profit_export_dir: str = str(PROJECT_ROOT / "exports" / "profit")
    # ProfitChart accounts (same password in Profit UI — stored in .env only)
    profit_password: str = ""
    profit_account_sim_id: str = "3368"
    profit_account_sim_name: str = "Filipe"
    profit_account_day_id: str = "14852883"
    profit_account_swing_id: str = "14852883"
    profit_account_live_name: str = "Filipe G. Monteiro"
    profit_live_style: str = "day"  # day | swing when PAPER_TRADING_MODE=false

    default_daily_loss_limit_brl: float = 500.0
    default_max_contracts: int = 10
    default_max_open_positions: int = 3

    scanner_cron_hour: int = 8
    scanner_cron_minute: int = 30
    scanner_min_volume: int = 5000
    scanner_symbols: str = "BOVA11"
    scanner_mode: str = "filipe_core14"  # filipe_core14 | ibov_top20 | custom
    scanner_include_bova_options: bool = True
    scanner_include_stock_options: bool = True
    bova_options_symbols: str = "BOVAX125,BOVAY125,BOVA11"

    # 2.0 — backtest gate before promoting ideas
    backtest_min_profit_factor: float = 1.3
    backtest_max_drawdown_pct: float = 8.0
    execution_backend: str = "profit"  # profit | paper | ntsl | clear

    enable_scheduler: bool = True
    optimization_max_workers: int = 2

    # Alerts (Telegram / Discord)
    alerts_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""

    # Dashboard auth (Streamlit login for VPS)
    dashboard_auth_enabled: bool = False
    dashboard_username: str = "filipe"
    dashboard_password: str = ""

    paper_trading_mode: bool = True

    # 3.0 — Structure Deck
    structure_types_enabled: str = (
        "scalp,covered_call,vertical,collar,bova_hedge,pair_spread"
    )
    max_pain_signal_enabled: bool = True
    greeks_stub_mode: bool = True
    max_portfolio_net_delta: float = 0.5
    walk_forward_auto_promote: bool = True
    walk_forward_interval_hours: int = 6
    walk_forward_promote_folds: int = 4
    walk_forward_use_bridge_candles: bool = False

    # 4.3 — Autonomous Engine + Strategy Lab
    autonomous_engine_enabled: bool = True
    autonomous_rankings_sync: bool = True
    rankings_sync_interval_hours: int = 6

    # 3.0 GA — board auth + VPS
    board_auth_enabled: bool = False
    board_username: str = "filipe"
    board_password: str = ""

    journal_auto_analyze: bool = True
    journal_analyze_limit: int = 5

    # 4.0-rc — optional ProfitChart co-start with dev.py
    profitchart_exe: str = ""
    profitchart_co_start: bool = True

    # 4.0 GA — autonomy engine (auto confirm/execute per sleeve)
    autonomy_enabled: bool = False
    autonomy_max_trades_per_day: int = 3
    auto_trading_on_sleeves: bool = True
    orchestrator_interval_sec: int = 45
    paper_orchestrator_interval_sec: int = 20
    paper_motor_ignore_b3_hours: bool = True
    paper_motor_auto_seed_ideas: bool = True
    paper_capital_brl: float = 30_000.0
    max_risk_per_trade_pct: float = 1.0
    max_position_pct: float = 15.0

    # 4.1 — futures watchlist + read-only social signals
    futures_watchlist_enabled: bool = True
    social_signals_enabled: bool = True

    # 4.2 — crypto watchlist + trade archaeology
    crypto_watchlist_enabled: bool = True
    binance_quotes_enabled: bool = True
    binance_api_base: str = "https://api.binance.com"
    archaeology_import_dir: str = str(PROJECT_ROOT / "exports" / "archaeology")
    crypto_paper_enabled: bool = True

    # 7.0 — Golden path (PETR4-only local perfection)
    golden_path_mode: bool = False
    low_ram_mode: bool = False
    streamlit_slim_mode: bool = False
    motor_journal_retention_days: int = 30
    golden_path_sessions_required: int = 5
    ram_budget_mb: int = 1200
    symbol_factory_max_per_week: int = 1
    arbitragem_bg_tests: bool = True

    @property
    def golden_path_symbol(self) -> str:
        return "PETR4"

    @property
    def low_ram_enabled(self) -> bool:
        """True when LOW_RAM_MODE or GOLDEN_PATH_MODE is on."""
        return self.low_ram_mode or self.golden_path_mode

    @property
    def streamlit_slim_enabled(self) -> bool:
        return self.low_ram_enabled or self.streamlit_slim_mode

    @property
    def ollama_runtime_enabled(self) -> bool:
        return self.ollama_enabled and not self.low_ram_enabled

    @property
    def social_signals_runtime_enabled(self) -> bool:
        return self.social_signals_enabled and not self.low_ram_enabled

    @property
    def streamlit_cache_ttl_sec(self) -> int:
        return 30 if self.low_ram_enabled else 60

    @property
    def desk_sse_interval_sec(self) -> int:
        if self.low_ram_enabled:
            return 60
        if self.golden_path_mode:
            return 30
        return 10

    @property
    def quotes_heartbeat_sec(self) -> int:
        return 30 if self.low_ram_enabled else 15

    @property
    def trader_desk_journal_limit(self) -> int:
        return 15 if self.low_ram_enabled else 35

    @property
    def effective_orchestrator_interval_sec(self) -> int:
        base = self.orchestrator_interval_sec
        return int(base * 1.5) if self.low_ram_enabled else base

    @property
    def effective_paper_orchestrator_interval_sec(self) -> int:
        base = self.paper_orchestrator_interval_sec
        return int(base * 1.5) if self.low_ram_enabled else base

    @property
    def effective_optimization_max_workers(self) -> int:
        return self.resource_profile.max_optimization_workers

    @property
    def resource_profile(self):
        """Lazy import — keeps config module light at import time."""
        from src.services.resource_profile import get_resource_profile

        return get_resource_profile(self)

    @property
    def scanner_symbol_list(self) -> list[str]:
        if self.golden_path_mode:
            return [self.golden_path_symbol]
        if self.scanner_mode == "filipe_core14":
            from src.services.filipe_universe import symbol_list

            symbols = symbol_list()
        elif self.scanner_mode == "ibov_top20":
            from src.services.ibov_universe import symbol_list

            symbols = symbol_list()
        else:
            symbols = [s.strip().upper() for s in self.scanner_symbols.split(",") if s.strip()]
        if self.scanner_include_bova_options:
            extras = [s.strip().upper() for s in self.bova_options_symbols.split(",") if s.strip()]
            seen = set(symbols)
            for s in extras:
                if s not in seen:
                    symbols.append(s)
                    seen.add(s)
            from src.services.filipe_universe import BOVA_UNDERLYING

            if BOVA_UNDERLYING not in seen:
                symbols.append(BOVA_UNDERLYING)
        return symbols

    @property
    def profit_export_path(self) -> Path:
        return Path(self.profit_export_dir)

    @property
    def archaeology_import_path(self) -> Path:
        return Path(self.archaeology_import_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
