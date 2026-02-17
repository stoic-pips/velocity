"""
Dunam Velocity – Supabase Sync
Fire-and-forget service to push trade results, bot status,
and account snapshots to Supabase for the mobile app.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from config.settings import get_settings


class SupabaseSync:
    """
    Lightweight Supabase client wrapper.
    All push methods are fire-and-forget: errors are logged but never raised,
    so they never block the scalper loop or API responses.
    """

    def __init__(self) -> None:
        self._client: Optional[Any] = None
        self._initialize()

    def _initialize(self) -> None:
        """Attempt to create the Supabase client. Silent on failure."""
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_key:
            print("[Supabase] No URL/Key configured – sync disabled.")
            return

        try:
            from supabase import create_client, Client
            self._client: Client = create_client(settings.supabase_url, settings.supabase_key)
            print("[Supabase] Client initialized.")
        except ImportError:
            print("[Supabase] supabase-py not installed – sync disabled.")
        except Exception as exc:
            print(f"[Supabase] Init error: {exc}")

    @property
    def is_connected(self) -> bool:
        """Whether the Supabase client is available."""
        return self._client is not None

    # ── Push Methods ────────────────────────────────────────────────────────

    def push_trade(self, trade_data: dict) -> None:
        """Insert a closed trade record into the 'trades' table."""
        if not self._client:
            return
        try:
            payload = {
                **trade_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._client.table("trades").insert(payload).execute()
            print(f"[Supabase] Trade pushed: {trade_data.get('action', 'unknown')}")
        except Exception as exc:
            print(f"[Supabase] push_trade error: {exc}")

    def push_bot_status(self, status: dict) -> None:
        """Upsert the bot's running/stopped state into the 'bot_status' table."""
        if not self._client:
            return
        try:
            # Map code-friendly names to DB-friendly names
            is_running = status.get("running")
            if is_running is None:
                is_running = status.get("is_running", False)

            payload = {
                "user_id": "velocity_bot",
                "is_running": is_running,
                "open_pl": status.get("open_pl", 0.0),
                "position_count": status.get("position_count", 0),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._client.table("bot_status").upsert(payload).execute()
            print(f"[Supabase] Bot status pushed: {payload}")
        except Exception as exc:
            print(f"[Supabase] push_bot_status error: {exc}")

    def push_account_snapshot(self, account_info: dict) -> None:
        """Insert an account balance/equity snapshot into 'account_snapshots'."""
        if not self._client:
            return
        try:
            # Filter only expected columns for 'account_snapshots'
            allowed_cols = {"login", "server", "balance", "equity", "margin", "free_margin", "profit", "currency"}
            filtered_info = {k: v for k, v in account_info.items() if k in allowed_cols}
            
            payload = {
                **filtered_info,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._client.table("account_snapshots").insert(payload).execute()
        except Exception as exc:
            print(f"[Supabase] push_account_snapshot error: {exc}")

    def sync_positions(self, positions: list[dict]) -> None:
        """
        Full sync of open positions:
        1. Delete all existing positions in DB.
        2. Insert current positions from MT5.
        3. Add timestamp.
        """
        if not self._client:
            return
        
        try:
            # 1. Delete existing (using a standard delete-all approach if possible, or by ticket)
            # For a full sync, deleting all is simplest to remove closed/phantom positions.
            self._client.table("positions").delete().neq("ticket", 0).execute()
            
            if not positions:
                return

            # 2. Filter core columns and add timestamp 
            allowed_cols = {"ticket", "symbol", "profit", "type", "volume", "price_open", "price_current"}
            payload = [
                {
                    **{k: v for k, v in pos.items() if k in allowed_cols},
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                for pos in positions
            ]
            
            # 3. Insert new state
            self._client.table("positions").insert(payload).execute()
            
        except Exception as exc:
            print(f"[Supabase] sync_positions error: {exc}")

    def get_bot_config(self) -> dict:
        """Fetch the latest bot configuration."""
        if not self._client:
            return {}
        try:
            response = self._client.table("bot_config").select("*").order("updated_at", desc=True).limit(1).execute()
            if response.data:
                return response.data[0]
            return {}
        except Exception as exc:
            # Silent fail for config fetch to avoid spamming logs if table empty
            return {}

    def push_config(self, settings: Any) -> None:
        """Insert current configuration to 'bot_config'."""
        if not self._client:
            return
        try:
            payload = {
                "mt5_login": str(settings.mt5_login) if settings.mt5_login else None,
                "mt5_server": settings.mt5_server,
                "small_profit_usd": settings.small_profit_usd,
                "max_open_positions": settings.max_open_positions,
                "strategy_enabled": getattr(settings, "strategy_enabled", True),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._client.table("bot_config").insert(payload).execute()
        except Exception as exc:
            print(f"[Supabase] push_config error: {exc}")

    # ── Risk & Monitor Methods ──────────────────────────────────────────────

    def fetch_risk_settings(self, user_id: str) -> Optional[dict]:
        """Fetch risk parameters from 'bot_configs'."""
        if not self._client:
            return None
        try:
            # Assuming 'bot_configs' table exists as per requirements
            response = self._client.table("bot_configs")\
                .select("risk_params, is_active")\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            
            if response.data:
                # Merge top-level fields if needed, but return risk_params primarily
                data = response.data
                risk_params = data.get("risk_params", {}) or {}
                # Ensure we return a dict that keys match what AccountMonitor expects
                return risk_params
            return None
        except Exception as exc:
            print(f"[Supabase] fetch_risk_settings error: {exc}")
            return None

    def update_bot_active_status(self, user_id: str, is_active: bool) -> None:
        """Update the active status of the bot for a user."""
        if not self._client:
            return
        try:
            self._client.table("bot_configs")\
                .update({"is_active": is_active, "updated_at": datetime.now(timezone.utc).isoformat()})\
                .eq("user_id", user_id)\
                .execute()
            print(f"[Supabase] Bot active status updated to {is_active} for {user_id}")
        except Exception as exc:
            print(f"[Supabase] update_bot_active_status error: {exc}")

    def push_notification(self, user_id: str, message: str, level: str = "info") -> None:
        """Push a notification to the dashboard (via 'notifications' table or similar)."""
        if not self._client:
            return
        try:
            # Assuming a 'notifications' table exists or using a method to push to frontend
            # If 'notifications' table doesn't exist, this will fail silently (logged).
            # Alternatively, could use 'bot_status' to convey messages.
            
            payload = {
                "user_id": user_id,
                "message": message,
                "level": level, # info, warning, critical, success
                "read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            self._client.table("notifications").insert(payload).execute()
            print(f"[Supabase] Notification pushed: {message}")
        except Exception as exc:
            print(f"[Supabase] push_notification error: {exc}")
