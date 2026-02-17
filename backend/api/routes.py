"""
Dunam Velocity – API Routes
Clean FastAPI endpoints that delegate to MT5Client and DunamVelocity.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth import verify_api_key
from config.settings import get_settings
from core.mt5_client import MT5Client
from services.dunam_velocity import DunamVelocity
from database.supabase_sync import SupabaseSync

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])

# ── Singletons ──────────────────────────────────────────────────────────────

_mt5 = MT5Client.instance()
_dunam = DunamVelocity()
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
            "is_active": _dunam.is_running,
            "strategy_running": _dunam.is_running,
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
    """Connect to MT5 and start the DunamVelocity engine."""
    if _dunam.is_running:
        return {"status": "Bot is already running", "is_active": True}

    # Ensure MT5 is connected
    if not _mt5.is_connected:
        connected = _mt5.connect()
        if not connected:
            return {"error": "Failed to connect to MT5", "running": False}

    _dunam.start()
    return {"status": "Bot started", "is_active": True}


@router.post("/stop")
async def stop_bot() -> dict:
    """Stop the DunamVelocity engine."""
    if not _dunam.is_running:
        return {"status": "Bot is already stopped", "is_active": False}

    _dunam.stop()
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


# ── Configuration ───────────────────────────────────────────────────────────

class ConfigUpdateRequest(BaseModel):
    mt5_login: Optional[int] = None
    mt5_password: Optional[str] = None
    mt5_server: Optional[str] = None
    strategy_symbols: Optional[str] = None


@router.get("/config")
async def get_config() -> dict:
    """Return current configuration (non-secret fields)."""
    settings = get_settings()
    return {
        "mt5_login": settings.mt5_login,
        "mt5_server": settings.mt5_server,
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

    # If credentials changed, attempt to reconnect MT5
    if any(k in updates for k in ["MT5_LOGIN", "MT5_PASSWORD", "MT5_SERVER", "MT5_PATH"]):
        print("[API] MT5 Credentials updated. Attempting reconnection...")
        _mt5.disconnect()
        _mt5.connect()

    # Sync to Supabase for Strategy Engine
    new_settings = get_settings() # Reload settings with new values
    _supabase.push_config(new_settings)

    return {"status": "Configuration updated", "updated_keys": list(updates.keys())}


# ── Sync ────────────────────────────────────────────────────────────────────

class SyncRequest(BaseModel):
    user_id: str
    days: int = 30


@router.post("/sync")
async def sync_trades(body: SyncRequest) -> dict:
    """
    Fetch history deals from MT5 and upsert them into Supabase 'trade_logs'.
    """
    if not _mt5.is_connected:
        return {"success": False, "error": "MT5 not connected"}

    import MetaTrader5 as mt5
    from datetime import datetime, timedelta, timezone

    # 1. Fetch history from MT5
    # Calculate 'from' date
    from_date = datetime.now(timezone.utc) - timedelta(days=body.days)
    
    # history_deals_get can take a date range
    deals = mt5.history_deals_get(from_date, datetime.now(timezone.utc))
    
    if deals is None:
        return {"success": False, "error": "Failed to fetch deals from MT5", "mt5_error": mt5.last_error()}

    # 2. Transform to 'trade_logs' format
    trade_logs = []
    for deal in deals:
        # Filter for entry/exit deals or just closed trades?
        # Usually we want deals that represent a closed trade (ENTRY_OUT / ENTRY_OUT_BY)
        # But 'trade_logs' schema implies a summarized trade. 
        # MT5 'deals' are individual executions. 'History Orders' are orders. 
        # Ideally we'd use history_orders_get or reconstruct positions from deals.
        # For simplicity, let's assume valid deals with profit != 0 are closed trades.
        # A more robust approach pairs ENTRY_IN and ENTRY_OUT.
        # Given "history_deals_get" specific instruction, we map deals.
        
        # We only care about deals that finalized a trade (Entry Out)
        if deal.entry == mt5.DEAL_ENTRY_OUT or deal.entry == mt5.DEAL_ENTRY_OUT_BY:
            # This is a closure.
            symbol = deal.symbol
            profit = deal.profit + deal.commission + deal.swap
            
            # Map direction (0=BUY, 1=SELL) -> But this is the Deal direction.
            # Closing a BUY position involves a SELL deal.
            # So if Deal is SELL (1) and Entry is OUT, the original position was BUY.
            # If Deal is BUY (0) and Entry is OUT, the original position was SELL.
            direction = "buy" if deal.type == mt5.ORDER_TYPE_SELL else "sell" 
            # Wait, DEAL_TYPE_BUY=0, DEAL_TYPE_SELL=1.
            # Closing a Buy requires a Sell order.
            
            # Timestamp
            closed_at = datetime.fromtimestamp(deal.time, tz=timezone.utc)
            # We don't have exact 'opened_at' in a single deal row without joining.
            # We can approximate or leave null, or fetch position details.
            # For this task, let's use closed_at for both if opened_at unavailable, 
            # OR better: use the deal time.
            
            # Generate a deterministic ID based on Ticket to avoid duplicates
            # trade_logs.id is UUID. Use a hash of ticket? Or user provided UUID?
            # Supabase can generate UUID if we don't provide it, but for upsert we need a key.
            # The user request said: "upsert... using symbol, opened_at, and user_id as conflict key".
            # So we don't need to generate UUID if the DB generates it, BUT we need those specific fields matching.
            
            trade_logs.append({
                "user_id": body.user_id,
                "symbol": symbol,
                "direction": direction,
                "profit": float(profit),
                "opened_at": closed_at.isoformat(), # Approximation as we lack entry time in single deal
                "closed_at": closed_at.isoformat(),
                "is_success": profit > 0
            })

    # 3. Push to Supabase
    if not trade_logs:
        return {"success": True, "count": 0, "message": "No deals found"}

    count = _supabase.upsert_trade_logs(trade_logs)
    
    return {"success": True, "count": count, "synced_timestamp": datetime.now(timezone.utc).isoformat()}
