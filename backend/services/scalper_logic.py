"""
Dunam Velocity – Scalper Logic (The Brain)
High-frequency monitoring loop that checks floating P&L and closes
all positions when the small-profit threshold is reached.
Runs in a background daemon thread so it never blocks the API.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from core.mt5_manager import MT5Manager
from config.settings import get_settings
from database.supabase_sync import SupabaseSync


class ScalperEngine:
    """
    The brain of the bot.
    Manages a background thread that continuously monitors floating P&L
    and triggers close-all when profit ≥ threshold.
    """

    def __init__(self) -> None:
        self._mt5: MT5Manager = MT5Manager.instance()
        self._supabase: SupabaseSync = SupabaseSync()
        self._thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._running: bool = False

    # ── Public API ──────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        """Whether the scalper loop is active."""
        return self._running

    def start(self) -> None:
        """Launch the background monitoring daemon thread."""
        if self._running:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._running = True

        # Push status to Supabase
        self._supabase.push_bot_status({"running": True})
        print("[Scalper] Engine started.")

    def stop(self) -> None:
        """Signal the monitor thread to stop gracefully."""
        if not self._running:
            return

        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)

        self._running = False

        # Push status to Supabase
        self._supabase.push_bot_status({"running": False})
        print("[Scalper] Engine stopped.")

    def check_small_profit(self, threshold_usd: Optional[float] = None) -> dict:
        """
        Check if total floating P&L ≥ threshold.
        If so, close all positions and return the result.
        """
        settings = get_settings()
        if threshold_usd is None:
            threshold_usd = settings.small_profit_usd

        positions = self._mt5.get_positions()
        if not positions:
            return {
                "triggered": False,
                "total_profit": 0.0,
                "message": "No open positions",
            }

        total_profit: float = sum(p["profit"] for p in positions)

        if total_profit >= threshold_usd:
            close_result = self._mt5.close_all_orders()

            # Log each closed trade to Supabase
            self._supabase.push_trade({
                "action": "small_profit_close",
                "total_profit": round(total_profit, 2),
                "threshold": threshold_usd,
                "positions_closed": close_result.get("closed", 0),
            })

            return {
                "triggered": True,
                "total_profit": round(total_profit, 2),
                "threshold": threshold_usd,
                "close_result": close_result,
            }

        return {
            "triggered": False,
            "total_profit": round(total_profit, 2),
            "threshold": threshold_usd,
            "message": f"Profit {total_profit:.2f} < threshold {threshold_usd:.2f}",
        }

    # ── Internal Loop ───────────────────────────────────────────────────────

    def _run_loop(self) -> None:
        """Background loop: polls P&L at the configured interval."""
        settings = get_settings()
        print(
            f"[Scalper] Monitor started – checking every {settings.profit_check_interval}s "
            f"(threshold: ${settings.small_profit_usd})"
        )

        while not self._stop_event.is_set():
            try:
                result = self.check_small_profit()

                if result["triggered"]:
                    print(
                        f"[Scalper] 🎯 Small-profit triggered at ${result['total_profit']:.2f} "
                        f"– closed {result['close_result']['closed']} position(s)."
                    )
                else:
                    print(
                        f"[Scalper] P&L: ${result['total_profit']:.2f} "
                        f"(threshold: ${result['threshold']:.2f})"
                    )

                # Periodic account snapshot
                account = self._mt5.get_account_info()
                if account:
                    self._supabase.push_account_snapshot(account)

            except Exception as exc:
                print(f"[Scalper] Error in loop: {exc}")

            self._stop_event.wait(settings.profit_check_interval)

        print("[Scalper] Monitor loop exited.")
