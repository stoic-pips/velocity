from pydantic import BaseModel, Field
from typing import Optional, Dict

class RuntimeConfig(BaseModel):
    """
    Configuration loaded dynamically from Supabase `bot_configs` table.
    Mirrors the structure of the database row + JSONB columns.
    """
    # Core Status
    is_active: bool = Field(default=False, description="Master switch for the bot strategy")
    
    # Credentials (Stored in mt5_credentials JSONB in DB)
    mt5_login: int = Field(default=0, description="MT5 Login ID")
    mt5_password: str = Field(default="", description="MT5 Password")
    mt5_server: str = Field(default="", description="MT5 Server Name")
    mt5_path: str = Field(default="", description="Path to terminal64.exe (Optional override)")
    
    # Strategy Params (Top-level columns or within JSONB)
    strategy_symbols: str = Field(default="EURUSD", description="Comma-separated symbols")
    strategy_timeframe: str = Field(default="M1", description="Timeframe")
    strategy_check_interval: float = Field(default=0.5, description="Loop sleep time")
    
    # Risk Params (Stored in risk_params JSONB in DB)
    small_profit_usd: float = Field(default=2.0)
    max_open_positions: int = Field(default=10)
    max_loss_percent: float = Field(default=10.0)
    risk_multiplier: float = Field(default=0.01)
    auto_lot_enabled: bool = Field(default=True)
    
    # Volatility Params (Stored in volatility_params JSONB in DB)
    volatility_filter_enabled: bool = Field(default=True)
    min_atr_threshold: float = Field(default=0.0001)
    volatility_avg_period: int = Field(default=20)
    extreme_vol_threshold: float = Field(default=2.5)

    class Config:
        extra = "ignore"
