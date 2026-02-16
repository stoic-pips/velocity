"""
Dunam Velocity – Main Entry Point
Initializes the FastAPI application and wires up all modules.
"""

import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router, _mt5, _scalper, _strategy
from config.settings import get_settings


# ── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle hooks."""
    settings = get_settings()

    # ── Startup ─────────────────────────────────────────────────────────
    print("=" * 60)
    print("  Dunam Velocity – MT5 Scalping Bot API")
    print(f"  Listening on {settings.host}:{settings.port}")
    print(f"  Small-profit threshold: ${settings.small_profit_usd}")
    print(f"  Max lot: {settings.max_lot_size}  Max positions: {settings.max_open_positions}")
    print("=" * 60)

    # Attempt MT5 connection at startup (non-fatal)
    connected = _mt5.connect()
    if not connected:
        print("[WARN] MT5 not connected – /api/start will retry.")

    yield

    # ── Shutdown ────────────────────────────────────────────────────────
    print("[Main] Shutting down...")
    if _scalper.is_running:
        _scalper.stop()
    if _strategy.is_running:
        _strategy.stop()
    _mt5.disconnect()
    print("[Main] Goodbye.")


# ── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Dunam Velocity",
    description="MT5 Scalping Bot REST API",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


# ── Root Health Check ───────────────────────────────────────────────────────

@app.get("/")
async def root() -> dict:
    """Health check – no auth required."""
    return {
        "app": "Dunam Velocity",
        "version": "2.0.0",
        "status": "online",
    }


# ── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
