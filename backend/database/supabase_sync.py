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
            payload = {
                "id": "velocity_bot",
                **status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._client.table("bot_status").upsert(payload).execute()
            print(f"[Supabase] Bot status pushed: {status}")
        except Exception as exc:
            print(f"[Supabase] push_bot_status error: {exc}")

    def push_account_snapshot(self, account_info: dict) -> None:
        """Insert an account balance/equity snapshot into 'account_snapshots'."""
        if not self._client:
            return
        try:
            payload = {
                **account_info,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._client.table("account_snapshots").insert(payload).execute()
        except Exception as exc:
            print(f"[Supabase] push_account_snapshot error: {exc}")
