"""
Dunam Velocity – API Routes
Clean FastAPI endpoints that delegate to MT5Manager and ScalperEngine.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth import verify_api_key
from core.mt5_manager import MT5Manager
from services.scalper_logic import ScalperEngine

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])

# ── Singletons ──────────────────────────────────────────────────────────────

_mt5 = MT5Manager.instance()
_scalper = ScalperEngine()


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
            "running": _scalper.is_running,
            "mt5_connected": _mt5.is_connected,
        },
        "account": account,
        "positions": positions,
        "position_count": len(positions),
    }


@router.post("/start")
async def start_bot() -> dict:
    """Connect to MT5 and start the scalper engine."""
    if _scalper.is_running:
        return {"status": "Bot is already running", "running": True}

    # Ensure MT5 is connected
    if not _mt5.is_connected:
        connected = _mt5.connect()
        if not connected:
            return {"error": "Failed to connect to MT5", "running": False}

    _scalper.start()
    return {"status": "Bot started", "running": True}


@router.post("/stop")
async def stop_bot() -> dict:
    """Stop the scalper engine."""
    if not _scalper.is_running:
        return {"status": "Bot is already stopped", "running": False}

    _scalper.stop()
    return {"status": "Bot stopped", "running": False}


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
