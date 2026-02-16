"""
Dunam Velocity – API Routes
Clean FastAPI endpoints that delegate to MT5Manager and ScalperEngine.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth import verify_api_key
from config.settings import get_settings
from core.mt5_manager import MT5Manager
from services.scalper_logic import ScalperEngine
from services.strategy_engine import StrategyEngine
from database.supabase_sync import SupabaseSync

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])

# ── Singletons ──────────────────────────────────────────────────────────────

_mt5 = MT5Manager.instance()
_scalper = ScalperEngine()
_strategy = StrategyEngine()
_supabase = SupabaseSync()


# ── Request / Response Models ───────────────────────────────────────────────

class OpenOrderRequest(BaseModel):
    symbol: str
    lot: float
    direction: str  # "BUY" | "SELL"
    sl: float = 0.0
    tp: float = 0.0
    comment: str = "Velocity"


class CloseOrderRequest(BaseModel):
    ticket: Optional[int] = None


class SmallProfitRequest(BaseModel):
    threshold: Optional[float] = None


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status() -> dict:
    """Return bot state, account info, and open positions."""
    account = _mt5.get_account_info()
    positions = _mt5.get_positions()
    return {
        "bot": {
            "is_active": _scalper.is_running,
            "strategy_running": _strategy.is_running,
            "mt5_connected": _mt5.is_connected,
        },
        "account": account,
        "positions": positions,
        "position_count": len(positions),
    }


@router.get("/symbols")
async def get_symbols() -> dict:
    """Return all available symbols grouped by category."""
    if not _mt5.is_connected:
        # Try to connect if not already
        _mt5.connect()
    
    return _mt5.get_categorized_symbols()


@router.post("/start")
async def start_bot() -> dict:
    """Connect to MT5 and start the scalper engine."""
    if _scalper.is_running:
        return {"status": "Bot is already running", "is_active": True}

    # Ensure MT5 is connected
    if not _mt5.is_connected:
        connected = _mt5.connect()
        if not connected:
            return {"error": "Failed to connect to MT5", "running": False}

    _scalper.start()
    _strategy.start()
    return {"status": "Bot started", "is_active": True}


@router.post("/stop")
async def stop_bot() -> dict:
    """Stop the scalper engine."""
    if not _scalper.is_running:
        return {"status": "Bot is already stopped", "is_active": False}

    _scalper.stop()
    _strategy.stop()
    return {"status": "Bot stopped", "is_active": False}


@router.post("/open")
async def open_order(body: OpenOrderRequest) -> dict:
    """Open a new position."""
    if not _mt5.is_connected:
        return {"success": False, "error": "MT5 not connected – start the bot first"}

    result = _mt5.open_order(
        symbol=body.symbol,
        lot=body.lot,
        direction=body.direction,
        sl=body.sl,
        tp=body.tp,
        comment=body.comment,
    )
    return result


@router.post("/close")
async def close_order(body: CloseOrderRequest) -> dict:
    """Close a position by ticket, or close all if ticket is omitted."""
    if not _mt5.is_connected:
        return {"success": False, "error": "MT5 not connected"}

    if body.ticket is not None:
        return _mt5.close_order(body.ticket)
    return _mt5.close_all_orders()


@router.post("/close-all")
async def close_all_orders() -> dict:
    """Explicit endpoint to close all open positions."""
    if not _mt5.is_connected:
        return {"success": False, "error": "MT5 not connected"}

    return _mt5.close_all_orders()


@router.post("/small-profit")
async def check_small_profit(body: SmallProfitRequest) -> dict:
    """Manually trigger a small-profit check."""
    return _scalper.check_small_profit(threshold_usd=body.threshold)


# ── Configuration ───────────────────────────────────────────────────────────

class ConfigUpdateRequest(BaseModel):
    mt5_login: Optional[int] = None
    mt5_password: Optional[str] = None
    mt5_server: Optional[str] = None
    small_profit_usd: Optional[float] = None
    auto_lot_enabled: Optional[bool] = None
    risk_multiplier: Optional[float] = None
    max_open_positions: Optional[int] = None
    strategy_enabled: Optional[bool] = None
    strategy_symbols: Optional[str] = None


@router.get("/config")
async def get_config() -> dict:
    """Return current configuration (non-secret fields)."""
    settings = get_settings()
    return {
        "mt5_login": settings.mt5_login,
        "mt5_server": settings.mt5_server,
        "small_profit_usd": settings.small_profit_usd,
        "auto_lot_enabled": settings.auto_lot_enabled,
        "risk_multiplier": settings.risk_multiplier,
        "max_open_positions": settings.max_open_positions,
        "strategy_enabled": settings.strategy_enabled,
        "strategy_symbols": settings.strategy_symbols,
    }


@router.post("/config")
async def update_config(body: ConfigUpdateRequest) -> dict:
    """Update configuration by patching the .env file and reloading settings."""
    env_path = Path(__file__).resolve().parent.parent / ".env"

    # Read existing .env content
    if env_path.exists():
        env_lines = env_path.read_text(encoding="utf-8").splitlines()
    else:
        env_lines = []

    # Build a mapping of updates
    updates: dict[str, str] = {}
    if body.mt5_login is not None:
        updates["MT5_LOGIN"] = str(body.mt5_login)
    if body.mt5_password is not None:
        updates["MT5_PASSWORD"] = body.mt5_password
    if body.mt5_server is not None:
        updates["MT5_SERVER"] = body.mt5_server
    if body.small_profit_usd is not None:
        updates["SMALL_PROFIT_USD"] = str(body.small_profit_usd)
    if body.auto_lot_enabled is not None:
        updates["AUTO_LOT_ENABLED"] = str(body.auto_lot_enabled).lower()
    if body.risk_multiplier is not None:
        updates["RISK_MULTIPLIER"] = str(body.risk_multiplier)
    if body.max_open_positions is not None:
        updates["MAX_OPEN_POSITIONS"] = str(body.max_open_positions)
    if body.strategy_enabled is not None:
        updates["STRATEGY_ENABLED"] = str(body.strategy_enabled).lower()
    if body.strategy_symbols is not None:
        updates["STRATEGY_SYMBOLS"] = body.strategy_symbols

    if not updates:
        return {"status": "No changes provided"}

    # Patch existing lines or append new ones
    found_keys: set[str] = set()
    new_lines: list[str] = []
    for line in env_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                found_keys.add(key)
                continue
        new_lines.append(line)

    # Append any keys that weren't already in the file
    for key, value in updates.items():
        if key not in found_keys:
            new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    # Clear settings cache so next call picks up new values
    get_settings.cache_clear()

    # Set environment variables for the current process too
    for key, value in updates.items():
        os.environ[key] = value

    # Sync to Supabase for Strategy Engine
    new_settings = get_settings() # Reload settings with new values
    _supabase.push_config(new_settings)

    return {"status": "Configuration updated", "updated_keys": list(updates.keys())}
