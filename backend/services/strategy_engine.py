import threading
import time
import traceback
from datetime import datetime, timezone

import MetaTrader5 as mt5
import pandas as pd
import numpy as np

from config.settings import get_settings
from core.mt5_manager import MT5Manager
from database.supabase_sync import SupabaseSync


class StrategyEngine:
    """
    Automated Entry Logic.
    Scans markets for SMA(10) + RSI(14) signals.
    """

    def __init__(self, check_interval: float = 1.0):
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        
        self._mt5 = MT5Manager.instance()
        self._supabase = SupabaseSync()
        
        # Track last trade time per symbol to enforce "one trade per candle"
        # Format: { "SYMBOL": timestamp_of_candle }
        self._last_trade_candles: dict[str, int] = {}

        self.check_interval = check_interval

    def start(self) -> None:
        """Start the strategy loop in a background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="StrategyEngine")
        self._thread.start()
        print("[Strategy] Engine started.")

    def stop(self) -> None:
        """Stop the strategy loop."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        print("[Strategy] Engine stopped.")

    @property
    def is_running(self) -> bool:
        """Check if the strategy thread is active."""
        return self._thread is not None and self._thread.is_alive()

    def _run_loop(self) -> None:
        """Main execution loop."""
        print(f"[Strategy] Starting loop. Interval: {self.check_interval}s")

        while not self._stop_event.is_set():
            try:
                settings = get_settings()
                
                # 1. Check if Strategy is Enabled
                is_enabled = settings.strategy_enabled
                if not is_enabled:
                    time.sleep(self.check_interval)
                    continue

                # 2. Check Max Positions
                open_positions = self._mt5.get_positions()
                if len(open_positions) >= settings.max_open_positions:
                    time.sleep(self.check_interval)
                    continue

                # 3. Scan Symbols from Settings
                symbols_str = settings.strategy_symbols
                symbols = [s.strip() for s in symbols_str.split(",") if s.strip()]
                
                for symbol in symbols:
                    if self._stop_event.is_set():
                        break
                    
                    try:
                        self.scan_market(symbol)
                    except Exception as e:
                        print(f"[Strategy] Error scanning {symbol}: {e}")

            except Exception as exc:
                print(f"[Strategy] Loop error: {exc}")
                traceback.print_exc()

            time.sleep(self.check_interval)

    def scan_market(self, symbol: str) -> None:
        """Fetch data, calculate indicators, and execute trade if signal found."""
        # 1. Fetch Candles (M1 or M5? User didn't specify timeframe. defaulting to M1 for scalping)
        timeframe = mt5.TIMEFRAME_M1
        count = 100
        
        # Verify symbol exists
        tick = self._mt5.get_tick(symbol)
        if not tick:
            return

        # copy_rates_from_pos(symbol, timeframe, start_pos, count)
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None or len(rates) < 20:
            return

        # 2. Prepare DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Calculates indicators (SMA 10, RSI 14)
        df = self.calculate_indicators(df)
        
        # 3. Check Signal on COMPLETED candle (index -2) 
        # Index -1 is the current forming candle. Index -2 is the last closed candle.
        # User said "one trade per 'candle'".
        # If we trade on close (confirmed signal), we look at -2.
        
        last_candle = df.iloc[-2]
        current_candle_time = int(last_candle['time'].timestamp())
        
        # Check if we already traded this candle
        if self._last_trade_candles.get(symbol) == current_candle_time:
            return

        close = last_candle['close']
        sma = last_candle['SMA_10']
        rsi = last_candle['RSI_14']
        
        # Verbose Logging for debugging
        if int(time.time()) % 10 == 0: # Log every 10s approximately per symbol to avoid spam
            print(f"[Strategy] {symbol} Scan: Close={close:.5f}, SMA={sma:.5f}, RSI={rsi:.1f}")

        signal = None
        
        # Slightly more sensitive logic: 
        # Buy: Oversold (RSI < 40) + Price below SMA (Mean Reversion)
        # Sell: Overbought (RSI > 60) + Price above SMA (Mean Reversion)
        if close < sma and rsi < 40:
            signal = "BUY"
        elif close > sma and rsi > 60:
            signal = "SELL"
            
        if signal:
            lot = self._calculate_lot_size(symbol)
            print(f"[Strategy] 🚀 {signal} Signal for {symbol} | Calculated Lot: {lot}")
            
            res = self._mt5.open_order(
                symbol=symbol,
                lot=lot,
                direction=signal,
                comment="Velocity Scalp"
            )
            
            if res['success']:
                print(f"[Strategy] Trade Executed: {res['ticket']}")
                # Mark this candle as traded
                self._last_trade_candles[symbol] = current_candle_time
                
                # Push trade intent to Supabase? (Already handled by close logic later, but maybe open too?)
                # Not currently required by user.
            else:
                print(f"[Strategy] Trade Failed: {res.get('error')}")

    def _calculate_lot_size(self, symbol: str) -> float:
        """
        Calculate lot size based on equity and risk multiplier.
        Formula: (Equity / 1000) * RiskMultiplier
        e.g. $1000 Equity / 1000 * 0.1 = 0.1 lots
        """
        settings = get_settings()
        
        if not settings.auto_lot_enabled:
            # Fallback to a safe minimum if auto-lot is off but we still need a value
            # Since we removed max_lot_size, we might want a 'manual_lot' or just default to 0.01
            return 0.01

        account = self._mt5.get_account_info()
        if not account:
            return 0.01
            
        equity = account.get("equity", 0.0)
        multiplier = settings.risk_multiplier
        
        # Basic calculation
        lot = (equity / 1000.0) * multiplier
        
        # Clamp to broker standards (minimum 0.01 usually)
        # We can try to get symbol info for min_lot
        import MetaTrader5 as mt5
        sym_info = mt5.symbol_info(symbol)
        if sym_info:
            min_lot = sym_info.volume_min
            max_lot = sym_info.volume_max
            step = sym_info.volume_step
            
            # Align with step
            lot = round(lot / step) * step
            lot = max(min_lot, min(max_lot, lot))
        else:
            lot = max(0.01, round(lot, 2))
            
        return round(lot, 2)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate SMA(10) and RSI(14)."""
        # SMA 10
        df['SMA_10'] = df['close'].rolling(window=10).mean()
        
        # RSI 14
        window = 14
        delta = df['close'].diff()
        
        # Make two series: gains and losses
        gain = delta.clip(lower=0)
        loss = -1 * delta.clip(upper=0)
        
        # Exponential Moving Average for Wilder's RSI (Standard)
        # com = (span - 1) / 2? No, alpha = 1/window for Wilder? 
        # Pandas ewm com = window - 1 is standard for some, but let's use:
        # alpha = 1 / window
        
        avg_gain = gain.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        df['RSI_14'] = 100 - (100 / (1 + rs))
        
        return df
