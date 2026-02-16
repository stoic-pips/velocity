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

    def check_risk_parameters(self, positions: Optional[list[dict]] = None) -> dict:
        """
        Check if total floating P&L exceeds Small Profit or Max Loss thresholds.
        Max Loss is calculated as a percentage of account equity.
        """
        settings = get_settings()
        threshold_profit = settings.small_profit_usd
        
        # Get account info for equity-based loss calculation
        account = self._mt5.get_account_info()
        if not account:
            return {"triggered": False, "total_profit": 0.0, "message": "MT5 not connected"}
            
        equity = account.get("equity", 0.0)
        # Calculate dynamic USD threshold (e.g. 10% of $10 = $1 loss allowed)
        threshold_loss_usd = -(equity * (settings.max_loss_percent / 100.0))

        if positions is None:
            positions = self._mt5.get_positions()

        if not positions:
            return {
                "triggered": False,
                "total_profit": 0.0,
                "message": "No open positions",
            }

        total_profit: float = sum(p["profit"] for p in positions)

        # 🎯 Case 1: Small Profit reached
        if total_profit >= threshold_profit:
            close_result = self._mt5.close_all_orders()
            self._supabase.push_trade({
                "action": "small_profit_close",
                "profit": round(total_profit, 2),
                "threshold": threshold_profit,
                "positions_closed": close_result.get("closed", 0),
            })
            return {
                "triggered": True,
                "reason": "small_profit",
                "total_profit": round(total_profit, 2),
                "close_result": close_result,
            }

        # 🛡️ Case 2: Maximum Loss reached (Equity % Circuit Breaker)
        if total_profit <= threshold_loss_usd:
            close_result = self._mt5.close_all_orders()
            self._supabase.push_trade({
                "action": "max_loss_circuit_breaker",
                "profit": round(total_profit, 2),
                "threshold": round(threshold_loss_usd, 2),
                "percent": settings.max_loss_percent,
                "positions_closed": close_result.get("closed", 0),
            })
            print(f"[Scalper] 🛡️ CIRCUIT BREAKER: {settings.max_loss_percent}% Loss hit (${total_profit:.2f} <= ${threshold_loss_usd:.2f})")
            return {
                "triggered": True,
                "reason": "max_loss",
                "total_profit": round(total_profit, 2),
                "close_result": close_result,
            }

        return {
            "triggered": False,
            "total_profit": round(total_profit, 2),
            "message": f"P&L {total_profit:.2f} within bounds ({threshold_loss_usd:.2f} to {threshold_profit:.2f})",
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
                # 1. Get current positions & sync to DB
                positions = self._mt5.get_positions()
                self._supabase.sync_positions(positions)

                # 2. Check logic and prepare heartbeat data
                total_profit = sum(p["profit"] for p in positions) if positions else 0.0
                position_count = len(positions) if positions else 0

                # Periodic heartbeat to status table for dashboard
                self._supabase.push_bot_status({
                    "running": True,
                    "open_pl": round(total_profit, 2),
                    "position_count": position_count
                })

                result = self.check_risk_parameters(positions=positions)

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

            # Always fetch latest settings for the wait interval
            current_settings = get_settings()
            self._stop_event.wait(current_settings.profit_check_interval)

        print("[Scalper] Monitor loop exited.")
