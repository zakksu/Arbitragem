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
    ollama_force_enabled: bool = False
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

    default_daily_loss_limit_brl: float = 100.0
    default_max_contracts: int = 10
    default_max_open_positions: int = 3
    motor_fixed_lot_shares: int = 100  # 12.0 — B3 standard lot; 0 = risk-based sizing
    stock_day_leverage_assumed: float = 50.0  # for margin/cost display (Clear up to 200x)

    scanner_cron_hour: int = 8
    scanner_cron_minute: int = 30
    scanner_min_volume: int = 5000
    scanner_symbols: str = "BOVA11"
    scanner_mode: str = "filipe_core5"  # filipe_core5 | filipe_core14 | filipe_core17 | ibov_top20 | custom
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
        "scalp,covered_call,vertical,collar,bova_hedge,pair_spread,"
        "stock_scalp_vwap,opening_range_break,mean_reversion_band,"
        "archaeology_bias_long,pulse_scalp"
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
    autonomy_enabled: bool = True
    autonomy_max_trades_per_day: int = 0  # 0 = unlimited (13.0)
    auto_trading_on_sleeves: bool = True
    orchestrator_interval_sec: int = 45
    paper_orchestrator_interval_sec: int = 20
    paper_motor_ignore_b3_hours: bool = True
    paper_motor_auto_seed_ideas: bool = True
    orchestrator_scheduler_enabled: bool = True
    autonomy_fast_track: bool = False
    paper_capital_brl: float = 1_000.0
    live_capital_brl: float = 1_000.0
    max_risk_per_trade_pct: float = 1.0
    max_position_pct: float = 15.0

    # 13.0 — Phase C + WIN cross-order
    phase_c_signed_off: bool = False
    phase_c_min_paper_days: int = 5
    phase_c_min_executed_fills: int = 20
    phase_c_max_motor_error_pct: float = 5.0
    profit_win_cross_order: bool = True

    # Profit execution ladder (no DLL required for paper / manual / NTSL)
    profit_exec_ladder: str = "auto"  # auto | paper_stub | manual_outbox | ntsl_export | dll_auto
    profit_ntsl_on_execute: bool = True
    profit_manual_auto_copy: bool = True
    profit_open_export_folder: bool = True

    # 4.1 — futures watchlist + read-only social signals
    futures_watchlist_enabled: bool = True
    social_signals_enabled: bool = True

    # 4.2 — crypto watchlist + trade archaeology
    crypto_watchlist_enabled: bool = False
    binance_quotes_enabled: bool = False
    binance_api_base: str = "https://api.binance.com"
    archaeology_import_dir: str = str(PROJECT_ROOT / "exports" / "archaeology")
    crypto_paper_enabled: bool = False

    # 7.0 — Golden path (PETR4-only local perfection)
    golden_path_mode: bool = False
    low_ram_mode: bool = False
    streamlit_slim_mode: bool = False
    motor_journal_retention_days: int = 30
    golden_path_sessions_required: int = 5
    ram_budget_mb: int = 1200
    symbol_factory_max_per_week: int = 1
    arbitragem_bg_tests: bool = True

    # 10.0 — Eternal Golden Path (replay training + strategy store + engine mind)
    replay_training_enabled: bool = True
    replay_training_interval_min: int = 30
    replay_parallel_workers: int = 2
    replay_max_bars_per_session: int = 120
    replay_feed_journal: bool = True
    replay_feed_wfo: bool = True
    replay_ollama_summary: bool = True
    strategy_store_enabled: bool = True
    profitchart_strategies_dir: str = ""
    strategy_store_extra_dirs: str = ""
    resource_ram_fraction: float = 0.8
    resource_gpu_fraction: float = 0.4
    engine_mind_enabled: bool = True
    knowledge_enabled: bool = True
    knowledge_max_chunks: int = 10000
    knowledge_db_path: str = ""
    knowledge_force_enabled: bool = False

    @property
    def knowledge_runtime_enabled(self) -> bool:
        if not self.knowledge_enabled:
            return False
        # 10.0 mastery path: allow corpus on golden path even when low-RAM trims other features
        if self.golden_path_mode:
            return True
        if self.low_ram_enabled and not self.knowledge_force_enabled:
            return False
        return True

    @property
    def effective_replay_workers(self) -> int:
        """Cap parallel replay jobs — uses up to ~80% host policy via worker count."""
        base = max(1, self.replay_parallel_workers)
        if self.low_ram_enabled:
            return 1
        return base

    @property
    def strategy_store_scan_paths(self) -> list:
        from pathlib import Path

        paths: list[Path] = []
        export_ntsl = Path(self.profit_export_dir) / "ntsl"
        if export_ntsl.exists():
            paths.append(export_ntsl)
        root_ntsl = PROJECT_ROOT / "exports" / "ntsl"
        if root_ntsl.exists() and root_ntsl not in paths:
            paths.append(root_ntsl)
        pack_ntsl = PROJECT_ROOT / "strategies" / "ntsl"
        if pack_ntsl.exists() and pack_ntsl not in paths:
            paths.append(pack_ntsl)
        if self.profitchart_strategies_dir:
            pc = Path(self.profitchart_strategies_dir)
            if pc.exists():
                paths.append(pc)
        for part in self.strategy_store_extra_dirs.split(","):
            p = part.strip()
            if p:
                extra = Path(p)
                if extra.exists() and extra not in paths:
                    paths.append(extra)
        return paths

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
        return self.ollama_enabled and (not self.low_ram_enabled or self.ollama_force_enabled)

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
        if self.scanner_mode == "filipe_core5":
            from src.services.filipe_universe import core5_symbol_list

            symbols = core5_symbol_list()
        elif self.scanner_mode == "filipe_core14":
            from src.services.filipe_universe import symbol_list

            symbols = symbol_list()
        elif self.scanner_mode == "filipe_core17":
            from src.services.filipe_universe import core17_symbol_list

            symbols = core17_symbol_list()
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
