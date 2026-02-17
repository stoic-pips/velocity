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

    def push_bot_status(self, status: dict, user_id: str = "velocity_bot") -> None:
        """Upsert the bot's running/stopped state into the 'bot_status' table."""
        if not self._client:
            return
        try:
            # Map code-friendly names to DB-friendly names
            is_running = status.get("running")
            if is_running is None:
                is_running = status.get("is_running", False)

            payload = {
                "user_id": user_id,
                "is_running": is_running,
                "open_pl": status.get("open_pl", 0.0),
                "position_count": status.get("position_count", 0),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            # Upsert using user_id as key. Schema might need to support user_id unique or PK.
            # Ideally bot_status PK is user_id. 
            # If current schema has 'id' as PK and default 'velocity_bot', we might have issues if we change user_id.
            # Assuming schema allows upsert on user_id or we map user_id -> id.
            # For now, let's map user_id to 'id' column if schema uses 'id'.
            # Based on schema.sql: id text primary key default 'velocity_bot'
            
            db_payload = {**payload}
            # We must provide both 'id' (PK) and 'user_id' (FK/Column) if they differ or if schema requires both.
            # If user_id is the PK, then id=user_id. 
            # If schema has separate user_id column that is NOT NULL, we must keep it.
            if "user_id" in db_payload:
                db_payload["id"] = db_payload["user_id"]
                
            self._client.table("bot_status").upsert(db_payload).execute()
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

    def get_bot_config(self, user_id: str) -> dict:
        """Fetch the latest bot configuration for a specific user."""
        if not self._client:
            return {}
        try:
            # Updated to use bot_configs and filter by user_id
            response = self._client.table("bot_configs")\
                .select("*")\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            
            if response.data:
                data = response.data
                risk = data.get("risk_params", {}) or {}
                creds = data.get("mt5_credentials", {}) or {}
                
                return {
                    "mt5_login": creds.get("login"),
                    "mt5_password": creds.get("password"),
                    "mt5_server": creds.get("server"),
                    "mt5_path": creds.get("path"),
                    
                    "small_profit_usd": risk.get("small_profit_usd"),
                    "max_open_positions": risk.get("max_open_positions"),
                    "max_loss_percent": risk.get("max_loss_percent"),
                    "risk_multiplier": risk.get("risk_multiplier"),
                    "auto_lot_enabled": risk.get("auto_lot_enabled"),
                    
                    "strategy_enabled": data.get("is_active", False),
                    "strategy_symbols": data.get("strategy_symbols"),
                    "strategy_timeframe": data.get("strategy_timeframe"),
                    "strategy_check_interval": data.get("strategy_check_interval"),
                    
                    "volatility_params": data.get("volatility_params", {}),
                    
                    "updated_at": data.get("updated_at")
                }
            return {}
        except Exception as exc:
            # Silent fail or log
            print(f"[Supabase] get_bot_config error: {exc}")
            return {}

    def get_active_config(self, user_id: str) -> Optional[Any]:
        """Fetch config and return as RuntimeConfig object."""
        # Avoid circular import
        from core.runtime_config import RuntimeConfig
        
        raw = self.get_bot_config(user_id)
        if not raw:
            return None
            
        try:
            # Map raw dict to RuntimeConfig fields
            # Note: get_bot_config already flattens some fields, but we need to map them correctly to RuntimeConfig
            # RuntimeConfig expects flat structure.
            # We might need to adjust get_bot_config to return exactly what RuntimeConfig expects 
            # OR map here.
            
            # Let's map explicitly for safety
            cfg = RuntimeConfig(
                is_active=raw.get("strategy_enabled", False),
                mt5_login=int(raw.get("mt5_login") or 0),
                mt5_server=raw.get("mt5_server", ""),
                
                small_profit_usd=float(raw.get("small_profit_usd") or 2.0),
                max_open_positions=int(raw.get("max_open_positions") or 10),
                
                strategy_symbols=raw.get("strategy_symbols", "EURUSD"),
                strategy_timeframe=raw.get("strategy_timeframe", "M1"),
                # We need other fields like auto_lot_enabled, risk_multiplier etc.
                # Currently get_bot_config doesn't return them.
                # We should update get_bot_config or fetching logic to get EVERYTHING.
            )
            return cfg
        except Exception as e:
            print(f"[Supabase] Error converting to RuntimeConfig: {e}")
            return None

    def listen_for_changes(self, user_id: str, callback: callable) -> None:
        """
        Subscribe to Realtime changes on 'bot_configs' for this user.
        """
        if not self._client:
            return

        def _handler(payload):
            # payload.new contains the updated row
            new_row = payload.get('new', {})
            if new_row.get('user_id') == user_id:
                print(f"[Realtime] Config update received for {user_id}")
                # We need to re-fetch or parse the new row to RuntimeConfig
                # The row is raw (has jsonb fields), so we might need a parser helper.
                # For simplicity, let's just trigger the callback which allows the caller to re-fetch
                # OR we can parse right here.
                # Re-fetching is safer to reuse mapping logic.
                callback()

        try:
            self._client.table('bot_configs:user_id=eq.' + user_id).on('*', _handler).subscribe()
            print(f"[Realtime] Listening for changes on bot_configs for {user_id}")
        except Exception as e:
             print(f"[Realtime] Error subscribing: {e}")

    def log_system_event(self, user_id: str, event: str, level: str = "info", details: dict = None) -> None:
        """Log system event to system_logs table."""
        if not self._client:
            return
        
        try:
             payload = {
                 "user_id": user_id,
                 "event": event,
                 "level": level,
                 "details": details or {},
                 "created_at": datetime.now(timezone.utc).isoformat()
             }
             self._client.table("system_logs").insert(payload).execute()
        except Exception as e:
            print(f"[Supabase] Error logging system event: {e}")

    def get_first_user_id(self) -> Optional[str]:
        """Fetch the first available user config ID to use as default."""
        if not self._client:
            return None
        try:
            # We use bot_configs as a proxy for 'users using the bot'
            response = self._client.table("bot_configs")\
                .select("user_id")\
                .limit(1)\
                .execute()
            
            if response.data:
                return response.data[0]["user_id"]
            return None
        except Exception as exc:
            print(f"[Supabase] get_first_user_id error: {exc}")
            return None

    def push_config(self, user_id: str, settings: Any) -> None:
        """
        Update configuration in 'bot_configs'. 
        Note: This effectively acts like update_bot_config but takes a generic settings object.
        """
        if not self._client:
            return
        try:
            payload = {
                "is_active": getattr(settings, "strategy_enabled", False),
                "strategy_symbols": getattr(settings, "strategy_symbols", None),
                "strategy_timeframe": getattr(settings, "strategy_timeframe", None),
                "risk_params": {
                    "small_profit_usd": settings.small_profit_usd,
                    "max_open_positions": settings.max_open_positions
                },
                "mt5_credentials": {
                    "login": str(settings.mt5_login) if settings.mt5_login else None,
                    "server": settings.mt5_server
                },
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            
            self._client.table("bot_configs")\
                .update(payload)\
                .eq("user_id", user_id)\
                .execute()
                
            print(f"[Supabase] Config pushed for {user_id}")
        except Exception as exc:
            print(f"[Supabase] push_config error: {exc}")

    # ── Risk & Monitor Methods ──────────────────────────────────────────────

    def fetch_risk_settings(self, user_id: str) -> Optional[dict]:
        """Fetch risk parameters from 'bot_configs'."""
        if not self._client:
            return None
        try:
            response = self._client.table("bot_configs")\
                .select("risk_params, is_active")\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            
            if response.data:
                data = response.data
                risk_params = data.get("risk_params", {}) or {}
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

    def upsert_trade_logs(self, trades: list[dict]) -> int:
        """Bulk upsert trade logs."""
        if not self._client or not trades:
            return 0
        try:
            result = self._client.table("trade_logs").upsert(trades).execute()
            return len(trades)
        except Exception as exc:
            print(f"[Supabase] upsert_trade_logs error: {exc}")
            return 0

    # ── Config Management (Fix for Duplicates) ──────────────────────────────

    def initialize_bot_config(self, user_id: str) -> dict:
        """
        On backend startup:
        - If the user already has a config → return it as-is, do NOT overwrite anything.
        - If no config exists → insert defaults for the first time only.
        """
        if not self._client:
            raise BotConfigLoadError("Supabase client not initialized")

        default_values = {
            "is_active": False,
            "timezone": "UTC",
        }

        try:
            # Upsert with on_conflict="user_id" and ignore_duplicates=True
            response = self._client.table("bot_configs").upsert(
                {"user_id": user_id, **default_values},
                on_conflict="user_id",
                ignore_duplicates=True
            ).execute()
            
            final_config = self._client.table("bot_configs")\
                .select("*")\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            
            if final_config.data:
                print(f"[Supabase] Config loaded for {user_id} (initialized if missing).")
                return final_config.data
            else:
                raise BotConfigLoadError("Failed to retrieve config after initialization")

        except Exception as exc:
            print(f"[Supabase] initialize_bot_config error: {exc}")
            raise BotConfigLoadError(f"Database error during config init: {exc}")

    def update_bot_config(self, user_id: str, new_params: dict) -> dict:
        """
        Only called when the user submits updated settings from the dashboard.
        Updates only the fields passed in new_params — never resets the whole row.
        """
        if not self._client:
            raise BotConfigLoadError("Supabase client not initialized")

        if not new_params:
            return {}

        try:
            payload = {
                **new_params,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            response = self._client.table("bot_configs")\
                .update(payload)\
                .eq("user_id", user_id)\
                .execute()
                
            if response.data:
                print(f"[Supabase] Config updated for {user_id}.")
                return response.data[0]
            else:
                 print(f"[Supabase] WARN: Update failed - no config found for {user_id}")
                 return {}

        except Exception as exc:
             print(f"[Supabase] update_bot_config error: {exc}")
             raise BotConfigLoadError(f"Database error during config update: {exc}")


class BotConfigLoadError(Exception):
    """Raised when bot configuration cannot be loaded or initialized."""
    pass

