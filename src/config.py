"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
    execution_backend: str = "ntsl"  # ntsl (Profit) | clear

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
    walk_forward_auto_promote: bool = False

    journal_auto_analyze: bool = True
    journal_analyze_limit: int = 5

    @property
    def scanner_symbol_list(self) -> list[str]:
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
