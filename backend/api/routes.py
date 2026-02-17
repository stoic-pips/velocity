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
    user_id: str # Required now for Supabase update
    mt5_login: Optional[int] = None
    mt5_password: Optional[str] = None
    mt5_server: Optional[str] = None
    strategy_symbols: Optional[str] = None
    strategy_timeframe: Optional[str] = None
    is_active: Optional[bool] = None
    risk_multiplier: Optional[float] = None


@router.get("/config")
async def get_config(user_id: Optional[str] = None) -> dict:
    """Return current configuration from Supabase."""
    # If we have a running bot with a config, we could return that.
    # But usually API should fetch from DB to be stateless/accurate.
    
    # Try to get user_id from running bot if not provided
    target_user_id = user_id or _dunam._user_id
    
    if not target_user_id or target_user_id == "velocity_bot":
        # Try to find ANY user config if we are in single-user mode
        target_user_id = _supabase.get_first_user_id()
    
    if not target_user_id:
        return {"error": "No configuration found. Please initialize via Dashboard."}

    config = _supabase.get_active_config(target_user_id)
    if not config:
        return {"error": "Failed to load config from Supabase"}
        
    return config.model_dump()


@router.post("/config")
async def update_config(body: ConfigUpdateRequest) -> dict:
    """Update configuration in Supabase (triggers realtime update in Bot)."""
    
    updates = {}
    
    # Map flat API fields to DB structure (JSONB for some)
    # We can use SupabaseSync.update_bot_config which expects a dict representing columns/jsonb
    
    # 1. Top Level
    if body.strategy_symbols is not None:
        updates["strategy_symbols"] = body.strategy_symbols
    if body.strategy_timeframe is not None:
        updates["strategy_timeframe"] = body.strategy_timeframe
    if body.is_active is not None:
        updates["is_active"] = body.is_active

    # 2. MT5 Credentials (JSONB merge not supported deeply by basic update, usually replace)
    # We need to fetch existing to merge, or use a customized sync method.
    # Let's fetch current config first to merge safely?
    # Or just push what we have if Supabase `push_config` handles it.
    # _supabase.update_bot_config does a direct update.
    
    # Let's construct a smart update payload.
    # Note: If we update 'mt5_credentials', we overwrite it unless we merge in code.
    current_config = _supabase.get_bot_config(body.user_id)
    
    if body.mt5_login or body.mt5_password or body.mt5_server:
        creds = current_config.get("mt5_credentials", {}) or {}
        if body.mt5_login is not None:
            creds["login"] = str(body.mt5_login)
        if body.mt5_password is not None:
             creds["password"] = body.mt5_password
        if body.mt5_server is not None:
             creds["server"] = body.mt5_server
        updates["mt5_credentials"] = creds
        
    if body.risk_multiplier is not None:
        risk = current_config.get("risk_params", {}) or {}
        risk["risk_multiplier"] = body.risk_multiplier
        updates["risk_params"] = risk

    if not updates:
         return {"status": "No changes provided"}

    updated = _supabase.update_bot_config(body.user_id, updates)
    
    if updated:
        return {"status": "Configuration updated", "updated_keys": list(updates.keys())}
    else:
        return {"status": "Update failed", "error": "Database write failed"}


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
