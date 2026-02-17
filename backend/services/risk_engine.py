"""
Dunam Velocity – Risk Engine
Implements Adaptive Profit Scaling and Account Monitoring for robust risk management.
"""

import threading
import time
import traceback
from datetime import datetime, timezone
from typing import Dict, Optional, Any

import pandas as pd
import MetaTrader5 as mt5

from config.settings import get_settings
from core.mt5_client import MT5Client
from database.supabase_sync import SupabaseSync


class AdaptiveScaling:
    """
    Adjusts profit targets based on market volatility (ATR).
    """

    def __init__(self, mt5_client: MT5Client):
        self._mt5 = mt5_client

    def get_dynamic_target(self, symbol: str) -> Dict[str, Any]:
        """
        Calculates dynamic profit target based on ATR.
        
        Returns:
            { "mode": "fixed"|"trailing", "target_usd": float|None, "tsl_pips": int|None }
        """
        settings = get_settings()
        
        # Default fallback
        Result = {
            "mode": "fixed",
            "target_usd": None,
            "tsl_pips": None
        }

        # Fetch account balance for percentage calculation
        account = self._mt5.get_account_info()
        if not account:
            return Result
        
        balance = account.get("balance", 0.0)
        daily_profit_target_pct = getattr(settings, "DAILY_PROFIT_TARGET_PCT", 2.0)
        
        # Calculate Base Target in USD
        base_target_usd = balance * (daily_profit_target_pct / 100.0)
        Result["target_usd"] = base_target_usd

        # Fetch ATR Data
        # We need enough data for ATR(14) and a daily average (e.g., 24 hours of M1 data? 
        # Or D1 timeframe? User said "daily average ATR". D1 ATR(14) vs Current H1/M1 ATR?)
        # Let's assume comparisons between Current ATR (M5/M15/H1) and Daily Average ATR.
        # User spec: "Rolling daily average ATR".
        # Let's use H1 candles for the last 24 hours (24 candles) for rolling average, 
        # and current H1 candle for current ATR.
        
        try:
            # Using H1 to approximate "Daily" rolling average
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)
            if rates is None or len(rates) < 20:
                return Result

            df = pd.DataFrame(rates)
            
            # Calculate ATR (14)
            df['H-L'] = df['high'] - df['low']
            df['H-PC'] = abs(df['high'] - df['close'].shift(1))
            df['L-PC'] = abs(df['low'] - df['close'].shift(1))
            df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
            df['ATR'] = df['TR'].rolling(window=14).mean()
            
            current_atr = df['ATR'].iloc[-1]
            daily_avg_atr = df['ATR'].iloc[-24:].mean() # Last 24 hours average
            
            atr_multiplier = getattr(settings, "ATR_MULTIPLIER", 2.0)
            
            # Check for Extreme Volatility
            if current_atr >= (atr_multiplier * daily_avg_atr):
                Result["mode"] = "trailing"
                Result["target_usd"] = None # Remove fixed cap
                Result["tsl_pips"] = getattr(settings, "TRAILING_STOP_PIPS", 10)
            else:
                Result["mode"] = "fixed"
                Result["target_usd"] = base_target_usd

        except Exception as e:
            print(f"[AdaptiveScaling] Error calculating target for {symbol}: {e}")
            Result["target_usd"] = base_target_usd # Fallback to fixed

        return Result


class AccountMonitor(threading.Thread):
    """
    Background thread to monitor account equity and enforce risk limits.
    Polls every 200ms (configurable).
    """

    def __init__(self, user_id: str):
        super().__init__(name="AccountMonitor", daemon=True)
        self.user_id = user_id
        self._stop_event = threading.Event()
        self._mt5 = MT5Client.instance()
        
        # We need a direct Supabase client or use SupabaseSync. 
        # Given requirement: "fetch ... from bot_configs filtered by user_id".
        # SupabaseSync is generic, but we can add a method or use the client directly if exposed.
        # For now, instantiating SupabaseSync.
        self._supabase = SupabaseSync()
        
        # State
        self.balance_at_day_start = 0.0
        self.config = {}

    def run(self) -> None:
        """Main polling loop."""
        print(f"[AccountMonitor] Starting for user {self.user_id}...")
        
        # 1. Init Config & Balance
        self._refresh_config()
        self._init_balance()
        
        monitor_interval = self.config.get("MONITOR_INTERVAL_MS", 200) / 1000.0

        while not self._stop_event.is_set():
            try:
                # A. Poll Account Info
                account = self._mt5.get_account_info()
                if not account:
                    time.sleep(1.0) # Wait for connection
                    continue

                current_equity = account.get("equity", 0.0)
                current_balance = account.get("balance", 0.0)
                
                # If balance changed (deposit/withdrawal), reset day start? 
                # For safety, let's stick to init value, OR update if balance increases?
                # Simplest interpretation: fixed "balance_at_day_start".
                
                # Calculate Metrics
                # floating_loss_usd: sum of negative profit positions
                positions = self._mt5.get_positions()
                floating_loss_usd = sum(p['profit'] for p in positions if p['profit'] < 0)
                
                daily_pnl_usd = current_equity - self.balance_at_day_start
                
                # Avoid division by zero
                base_balance = self.balance_at_day_start if self.balance_at_day_start > 0 else 1.0
                
                loss_pct = (abs(floating_loss_usd) / base_balance) * 100
                profit_pct = (daily_pnl_usd / base_balance) * 100
                
                # Risk Parameters
                daily_loss_limit_pct = self.config.get("DAILY_LOSS_LIMIT_PCT", 1.0)
                daily_profit_target_pct = self.config.get("DAILY_PROFIT_TARGET_PCT", 2.0)
                
                # B. Blow-Up Prevention (Loss Side)
                hard_floor_hit = current_equity <= (self.balance_at_day_start * 0.95)
                loss_limit_hit = loss_pct >= daily_loss_limit_pct

                if loss_limit_hit or hard_floor_hit:
                    self._trigger_emergency_protocol(loss_pct, hard_floor_hit)
                    break # Stop monitor after lockdown

                # C. Profit Lock-In
                if profit_pct >= daily_profit_target_pct:
                    self._trigger_profit_lock(profit_pct)
                    break # Stop monitor after pause

            except Exception as e:
                print(f"[AccountMonitor] Loop Error: {e}")
                traceback.print_exc()
            
            time.sleep(monitor_interval)
            
        print("[AccountMonitor] Thread stopped.")

    def stop(self) -> None:
        """Stop the monitor thread."""
        self._stop_event.set()

    def _init_balance(self) -> None:
        """Initialize balance at start of monitoring session."""
        account = self._mt5.get_account_info()
        if account:
            self.balance_at_day_start = account.get("balance", 0.0)
        else:
            self.balance_at_day_start = 0.0
            print("[AccountMonitor] WARN: Could not fetch initial balance. Defaulting to 0.")

    def _refresh_config(self) -> None:
        """Fetch latest risk config from Supabase."""
        # Fallback values
        default_config = {
            "DAILY_LOSS_LIMIT_PCT": 1.0,
            "DAILY_PROFIT_TARGET_PCT": 2.0,
            "TRAILING_STOP_PIPS": 10,
            "ATR_MULTIPLIER": 2.0,
            "MONITOR_INTERVAL_MS": 200
        }
        
        try:
            # TODO: Add specific method to SupabaseSync to fetch bot_configs by user_id
            # For now, using a potential method or falling back to defaults.
            # Assuming SupabaseSync has a client we can use or we extend it.
            # self.config = self._supabase.get_risk_config(self.user_id) or default_config
            
            # Implementation note: Since SupabaseSync is not passed the user_id in __init__ in current codebase,
            # we need to ensure we can query. 
            # Ideally:
            fetched = self._supabase.fetch_risk_settings(self.user_id)
            if fetched:
                self.config = fetched
            else:
                self.config = default_config
                print("[AccountMonitor] Using default risk config (DB fetch failed or empty).")
                
        except Exception as e:
            print(f"[AccountMonitor] Config fetch failed: {e}. Using defaults.")
            self.config = default_config

    def _trigger_emergency_protocol(self, loss_pct: float, hard_floor: bool) -> None:
        """Executed when loss limit is breached."""
        print(f"[AccountMonitor] 🚨 CRITICAL: Risk Limit Hit! Loss: {loss_pct:.2f}% (HardFloor: {hard_floor})")
        
        # 1. Close All
        self._mt5.close_all_orders()
        
        # 2. Deactivate Bot
        self._supabase.update_bot_active_status(self.user_id, False)
        
        # 3. Notify
        msg = f"CRITICAL: Loss limit reached ({loss_pct:.2f}%). All positions closed. Bot deactivated."
        self._supabase.push_notification(self.user_id, msg, "critical")

    def _trigger_profit_lock(self, profit_pct: float) -> None:
        """Executed when profit target is reached."""
        print(f"[AccountMonitor] 💰 SUCCESS: Profit Target Hit! Profit: {profit_pct:.2f}%")
        
        # 1. Close All
        self._mt5.close_all_orders()
        
        # 2. Pause Bot
        self._supabase.update_bot_active_status(self.user_id, False)
        
        # 3. Notify
        msg = f"SUCCESS: Profit target reached ({profit_pct:.2f}%). Positions closed. Bot paused for the day."
        self._supabase.push_notification(self.user_id, msg, "success")
