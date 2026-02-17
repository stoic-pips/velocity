import threading
import time
import traceback
from datetime import datetime, timezone
from typing import List, Dict, Optional

import MetaTrader5 as mt5
import pandas as pd
import numpy as np

from config.settings import get_settings
from core.mt5_client import MT5Client
from database.supabase_sync import SupabaseSync
from services.base_strategy import BaseStrategy


class DunamVelocity(BaseStrategy):
    """
    Dunam Velocity Strategy Implementation.
    Combines high-frequency scalping logic (Exit) with SMA+RSI entry signals (Entry).
    """

    def __init__(self, check_interval: float = 1.0):
        self.check_interval = check_interval
        
        # Threading control
        self._stop_event = threading.Event()
        self._entry_thread: Optional[threading.Thread] = None
        self._exit_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Dependencies
        self._mt5 = MT5Client.instance()
        self._supabase = SupabaseSync()
        
        # State
        # Track last trade time per symbol to enforce "one trade per candle"
        # Format: { "SYMBOL": timestamp_of_candle }
        self._last_trade_candles: Dict[str, int] = {}
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> None:
        """Start both entry (scanning) and exit (monitoring) loops."""
        if self._is_running:
            return

        print("[DunamVelocity] Starting engine...")
        self._stop_event.clear()
        self._is_running = True
        
        self._entry_thread = threading.Thread(target=self._entry_loop, daemon=True, name="Velocity-Entry")
        self._exit_thread = threading.Thread(target=self._exit_loop, daemon=True, name="Velocity-Exit")
        
        self._entry_thread.start()
        self._exit_thread.start()
        
        self._supabase.push_bot_status({"running": True})
        print("[DunamVelocity] Engine started.")

    def stop(self) -> None:
        """Stop all background loops."""
        if not self._is_running:
            return

        print("[DunamVelocity] Stopping engine...")
        self._stop_event.set()
        
        if self._entry_thread and self._entry_thread.is_alive():
            self._entry_thread.join(timeout=2.0)
        
        if self._exit_thread and self._exit_thread.is_alive():
            self._exit_thread.join(timeout=2.0)
            
        self._is_running = False
        self._supabase.push_bot_status({"running": False})
        print("[DunamVelocity] Engine stopped.")

    # ── Entry Logic (formerly StrategyEngine) ─────────────────────────────────

    def _entry_loop(self) -> None:
        """Continuous market scanning loop."""
        print(f"[Entry] Loop started. Interval: {self.check_interval}s")

        while not self._stop_event.is_set():
            try:
                settings = get_settings()
                
                # 1. Check if Strategy is Enabled
                if not settings.strategy_enabled:
                    time.sleep(settings.strategy_check_interval)
                    continue

                # 2. Check Max Positions
                open_positions = self._mt5.get_positions()
                if len(open_positions) >= settings.max_open_positions:
                    time.sleep(settings.strategy_check_interval)
                    continue

                # 3. Scan Symbols
                symbols_str = settings.strategy_symbols
                symbols = [s.strip() for s in symbols_str.split(",") if s.strip()]
                
                for symbol in symbols:
                    if self._stop_event.is_set():
                        break
                    
                    try:
                        self._scan_market(symbol)
                    except Exception as e:
                        print(f"[Entry] Error scanning {symbol}: {e}")

            except Exception as exc:
                print(f"[Entry] Loop error: {exc}")
                traceback.print_exc()

            time.sleep(get_settings().strategy_check_interval)

    def _scan_market(self, symbol: str) -> None:
        """Fetch data, calculate signals, and execute trades."""
        settings = get_settings()
        
        # 1. Map Timeframe
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
        }
        timeframe = tf_map.get(settings.strategy_timeframe, mt5.TIMEFRAME_M1)
        
        # Verify symbol and get rates
        tick = self._mt5.get_tick(symbol)
        if not tick:
             # Try selecting if missing
            if mt5.symbol_select(symbol, True):
                 time.sleep(0.1)
                 tick = self._mt5.get_tick(symbol)
            if not tick:
                return

        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
        if rates is None or len(rates) < 20:
            return

        # 2. DataFrame & Indicators
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df = self._calculate_indicators(df)
        
        # 3. Check Signal
        # live_candle_signals: True=current(-1), False=closed(-2)
        signal_index = -1 if settings.live_candle_signals else -2
        target_candle = df.iloc[signal_index]
        current_candle_time = int(target_candle['time'].timestamp())
        
        # Enforce one trade per candle (if not running in live tick mode)
        if not settings.live_candle_signals and self._last_trade_candles.get(symbol) == current_candle_time:
            return

        # 4. Volatility Filter
        vol_check = self._check_volatility(symbol, df)
        if not vol_check['allowed']:
            return

        close = target_candle['close']
        sma = target_candle['SMA_10']
        rsi = target_candle['RSI_14']
        
        # Debug logging (throttled)
        if int(time.time()) % 60 == 0: 
            print(f"[Entry] {symbol}: Close={close:.5f}, SMA={sma:.5f}, RSI={rsi:.1f}")

        signal: Optional[str] = None
        
        # Logic: Mean Reversion
        if close < sma and rsi < 40:
            signal = "BUY"
        elif close > sma and rsi > 60:
            signal = "SELL"
            
        if signal:
            lot = self._calculate_lot_size(symbol)
            print(f"[Entry] 🚀 {signal} Signal for {symbol} | Lot: {lot}")
            
            res = self._mt5.open_order(
                symbol=symbol,
                lot=lot,
                direction=signal,
                comment="Velocity Scalp"
            )
            
            if res['success']:
                print(f"[Entry] Trade Executed: {res['ticket']}")
                self._last_trade_candles[symbol] = current_candle_time
            else:
                print(f"[Entry] Trade Failed: {res.get('error')}")

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate SMA(10), RSI(14), and ATR(14)."""
        # SMA 10
        df['SMA_10'] = df['close'].rolling(window=10).mean()
        
        # RSI 14
        window = 14
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -1 * delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
        rs = avg_gain / avg_loss
        df['RSI_14'] = 100 - (100 / (1 + rs))

        # ATR 14
        df['H-L'] = df['high'] - df['low']
        df['H-PC'] = abs(df['high'] - df['close'].shift(1))
        df['L-PC'] = abs(df['low'] - df['close'].shift(1))
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        df['ATR_14'] = df['TR'].rolling(window=14).mean()
        
        return df

    def _check_volatility(self, symbol: str, df: pd.DataFrame) -> Dict:
        """Check ATR threshold, volatility expansion, and spread cost."""
        settings = get_settings()
        if not settings.volatility_filter_enabled:
            return {'allowed': True}

        # 1. ATR Check
        current_atr = df['ATR_14'].iloc[-1]
        if current_atr < settings.min_atr_threshold:
            return {'allowed': False, 'reason': 'Low ATR'}

        # 2. Volatility Expansion
        current_vol = df['TR'].iloc[-1]
        avg_vol = df['ATR_14'].iloc[-20:].mean()
        if current_vol < avg_vol:
            return {'allowed': False, 'reason': 'Contracting Volatility'}

        # 3. Spread Protection
        info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        
        if info and tick:
            spread_points = tick.ask - tick.bid
            if info.point > 0 and info.trade_tick_value > 0:
                vol_min = info.volume_min if info.volume_min > 0 else 0.01
                spread_cost = (spread_points / info.point) * info.trade_tick_value * vol_min
                
                target_usd = settings.small_profit_usd
                if spread_cost > (target_usd * 0.3):
                    return {'allowed': False, 'reason': 'High Spread'}

        return {'allowed': True}

    def _calculate_lot_size(self, symbol: str) -> float:
        """Calculate dynamic lot size based on equity and risk multiplier."""
        settings = get_settings()
        if not settings.auto_lot_enabled:
            return 0.01

        account = self._mt5.get_account_info()
        if not account:
            return 0.01
            
        equity = account.get("equity", 0.0)
        lot = (equity / 1000.0) * settings.risk_multiplier
        
        # Clamp to broker limits
        sym_info = mt5.symbol_info(symbol)
        if sym_info:
            step = sym_info.volume_step
            if step > 0:
                lot = round(lot / step) * step
            lot = max(sym_info.volume_min, min(sym_info.volume_max, lot))
        else:
            lot = max(0.01, round(lot, 2))
            
        return round(lot, 2)

    # ── Exit Logic (formerly ScalperEngine) ──────────────────────────────────

    def _exit_loop(self) -> None:
        """Monitor P&L and Trigger Entry/Exit Actions."""
        settings = get_settings()
        print(f"[Exit] Loop started. Check Interval: {settings.profit_check_interval}s")

        while not self._stop_event.is_set():
            try:
                # 1. Sync Positions
                positions = self._mt5.get_positions()
                self._supabase.sync_positions(positions)

                # 2. Heartbeat / Status
                total_profit = sum(p["profit"] for p in positions) if positions else 0.0
                self._supabase.push_bot_status({
                    "running": True,
                    "open_pl": round(total_profit, 2),
                    "position_count": len(positions)
                })

                # 3. Check Risk & Profit
                self._check_risk_parameters(positions, total_profit)

                # 4. Snapshot
                account = self._mt5.get_account_info()
                if account:
                    self._supabase.push_account_snapshot(account)

            except Exception as exc:
                print(f"[Exit] Loop error: {exc}")

            time.sleep(get_settings().profit_check_interval)

    def _check_risk_parameters(self, positions: List[Dict], total_profit: float) -> None:
        """Check for Small Profit Take or Max Loss Circuit Breaker."""
        settings = get_settings()
        threshold_profit = settings.small_profit_usd
        
        # Calculate dynamic Max Loss
        account = self._mt5.get_account_info()
        equity = account.get("equity", 1000.0) if account else 1000.0
        threshold_loss_usd = -(equity * (settings.max_loss_percent / 100.0))

        if not positions:
            return

        # Case 1: Small Profit Reached
        if total_profit >= threshold_profit:
            res = self._mt5.close_all_orders()
            self._supabase.push_trade({
                "action": "small_profit_close",
                "profit": round(total_profit, 2),
                "threshold": threshold_profit,
                "positions_closed": res.get("closed", 0),
            })
            print(f"[Exit] 🎯 Profit Target Hit: ${total_profit:.2f}. Closed {res.get('closed')} trades.")

        # Case 2: Max Loss Circuit Breaker
        elif total_profit <= threshold_loss_usd:
            res = self._mt5.close_all_orders()
            self._supabase.push_trade({
                "action": "max_loss_circuit_breaker",
                "profit": round(total_profit, 2),
                "threshold": round(threshold_loss_usd, 2),
                "percent": settings.max_loss_percent,
                "positions_closed": res.get("closed", 0),
            })
            print(f"[Exit] 🛡️ CIRCUIT BREAKER: {settings.max_loss_percent}% Loss hit (${total_profit:.2f}). Closed all.")
