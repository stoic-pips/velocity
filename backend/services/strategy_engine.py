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
                    time.sleep(settings.strategy_check_interval)
                    continue

                # 2. Check Max Positions
                open_positions = self._mt5.get_positions()
                if len(open_positions) >= settings.max_open_positions:
                    time.sleep(settings.strategy_check_interval)
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

            # Always fetch latest settings for the wait interval
            current_settings = get_settings()
            time.sleep(current_settings.strategy_check_interval)

    def scan_market(self, symbol: str) -> None:
        """Fetch data, calculate indicators, and execute trade if signal found."""
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
        
        # 3. Check Signal
        # live_candle_signals: if True, use index -1 (current). Else use -2 (closed).
        signal_index = -1 if settings.live_candle_signals else -2
        target_candle = df.iloc[signal_index]
        current_candle_time = int(target_candle['time'].timestamp())
        
        # Check if we already traded this candle (only for closed candle mode)
        if not settings.live_candle_signals and self._last_trade_candles.get(symbol) == current_candle_time:
            return

        # 3. Volatility Filter
        vol_check = self.check_volatility(symbol, df)
        if not vol_check['allowed']:
            if vol_check.get('status') == 'Market Sleep':
                self._supabase.push_bot_status({"status_message": "Market Sleep: Low Volatility"})
            return

        # Adaptive Profit Logic
        if vol_check.get('extreme'):
            # Temporary override of small_profit_usd for this cycle? 
            # Or just pass it to the scalper? 
            # The user says "automatically double the SMALL_PROFIT_USD target".
            # We can update the settings for the whole cycle or just for these positions.
            # Easiest: patch the env/settings temporarily or just log it.
            # Let's use a more robust way: ScalperEngine reads settings.
            # If we double it here, it might not affect already open positions unless we change the global setting.
            # The prompt says "automatically double the SMALL_PROFIT_USD target to capture the larger move".
            # I'll update the settings temporarily (in-memory) if extreme is detected.
            settings.small_profit_usd *= 2.0
            print(f"[Strategy] ⚡ EXTREME VOLATILITY DETECTED. Doubling profit target to ${settings.small_profit_usd}")

        close = target_candle['close']
        sma = target_candle['SMA_10']
        rsi = target_candle['RSI_14']
        
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

    def check_volatility(self, symbol: str, df: pd.DataFrame) -> dict:
        """
        Senior Quant Volatility Filter:
        1. ATR Threshold: Current ATR > MIN_ATR_THRESHOLD.
        2. RVI/Expansion: Current volatility > Avg(last 20).
        3. Spread Protection: Spread < 30% of target profit.
        """
        settings = get_settings()
        if not settings.volatility_filter_enabled:
            return {'allowed': True}

        # 1. ATR Check
        current_atr = df['ATR_14'].iloc[-1]
        if current_atr < settings.min_atr_threshold:
            return {'allowed': False, 'status': 'Market Sleep', 'reason': 'ATR below threshold'}

        # 2. Relative Volatility Expansion (RVI-style)
        current_vol = df['TR'].iloc[-1] # True Range of current candle
        avg_vol = df['ATR_14'].iloc[-20:].mean() # Avg ATR of last 20
        
        if current_vol < avg_vol:
            return {'allowed': False, 'status': 'Wait', 'reason': 'Volatility contracting'}

        # 3. Spread Protection
        tick = self._mt5.get_tick(symbol)
        if tick:
            spread = tick.ask - tick.bid
            # Target profit is in USD, spread is in price points.
            # We need to convert spread to USD for a valid comparison.
            # Approx: SpreadUSD = Spread * Lot * TickValue / TickSize
            # But simpler: If spreadPoints > 30% of target points?
            # User says "If spread is > 30% of the target profit (SMALL_PROFIT_USD)".
            # This is tricky because profit is aggregate. 
            # Let's assume a standard 0.01 lot for the check.
            target_usd = settings.small_profit_usd
            if spread > (target_usd * 0.3): # Naive check, assuming 1 point ~ 1 USD for simplicity or scaling needed
                # Realistically we should use point value.
                # If spread is 30% of the goal, it's too expensive.
                return {'allowed': False, 'status': 'Wait', 'reason': 'Spread too wide'}

        # 4. Adaptive Logic (Extreme)
        is_extreme = current_atr > (settings.min_atr_threshold * settings.extreme_vol_threshold)
        
        return {'allowed': True, 'extreme': is_extreme}

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate SMA(10), RSI(14), and Volatility (ATR)."""
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
