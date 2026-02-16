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
    profit_check_interval: int = Field(default=5, description="Seconds between profit checks")
    max_lot_size: float = Field(default=1.0, description="Maximum allowed lot size per order")
    max_open_positions: int = Field(default=10, description="Maximum simultaneous open positions")
    strategy_enabled: bool = True

    # ── Supabase ────────────────────────────────────────────────────────────
    supabase_url: str = Field(default="", description="Supabase project URL")
    supabase_key: str = Field(default="", description="Supabase anon/service key")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton accessor for application settings."""
    return Settings()
