"""
Dunam Velocity – Settings
Centralized configuration using Pydantic BaseSettings with .env auto-load.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """All application settings loaded from environment variables."""

    # ── API / Auth ──────────────────────────────────────────────────────────
    api_key: str = Field(default="change-me", description="Shared API key for mobile ↔ backend")
    host: str = Field(default="0.0.0.0", description="Server bind address")
    port: int = Field(default=8000, description="Server port")

    # ── MetaTrader 5 ────────────────────────────────────────────────────────
    mt5_login: int = Field(default=0, description="MT5 account login")
    mt5_password: str = Field(default="", description="MT5 account password")
    mt5_server: str = Field(default="", description="MT5 broker server")
    mt5_path: str = Field(default="", description="Path to terminal64.exe")

    # ── Scalper / Risk ──────────────────────────────────────────────────────
    small_profit_usd: float = Field(default=2.0, description="Small-profit close threshold (USD)")
    profit_check_interval: float = Field(default=1.0, description="Seconds between profit checks")
    auto_lot_enabled: bool = Field(default=True, description="Calculate lot size automatically based on equity")
    risk_multiplier: float = Field(default=0.01, description="Lots per $1000 equity")
    max_open_positions: int = Field(default=10, description="Maximum simultaneous open positions")
    max_loss_percent: float = Field(default=10.0, description="Max floating loss as % of equity before close-all")
    strategy_enabled: bool = True
    strategy_symbols: str = Field(default="EURUSD,USDJPY,GBPUSD,Volatility 75 Index", description="Comma-separated list of symbols to scan")
    strategy_check_interval: float = Field(default=0.5, description="Seconds between strategy scans")
    strategy_timeframe: str = Field(default="M1", description="MT5 Timeframe (M1, M5, M15, M30, H1)")
    live_candle_signals: bool = Field(default=False, description="Trade on current forming candle if True")
    
    # ── Volatility Filter ──────────────────────────────────────────────────
    volatility_filter_enabled: bool = Field(default=True, description="Enable ATR and RVI volatility filtering")
    min_atr_threshold: float = Field(default=0.0001, description="Minimum ATR to allow trades")
    volatility_avg_period: int = Field(default=20, description="Period for relative volatility average")
    extreme_vol_threshold: float = Field(default=2.5, description="ATR multiplier to trigger profit doubling")

    # ── Supabase ────────────────────────────────────────────────────────────
    supabase_url: str = Field(default="", description="Supabase project URL")
    supabase_key: str = Field(default="", description="Supabase anon/service key")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton accessor for application settings."""
    return Settings()
