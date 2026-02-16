# Start script
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import MetaTrader5 as mt5
from config.settings import get_settings

# Initialize MT5
if not mt5.initialize():
    print("MT5 Init failed")
    sys.exit(1)

settings = get_settings()
symbols = [s.strip() for s in settings.strategy_symbols.split(",") if s.strip()]
target_usd = settings.small_profit_usd
threshold = target_usd * 0.3

print(f"Target Profit: ${target_usd}")
print(f"Spread Threshold (USD/Points mixed?): {threshold}")

print(f"\nScanning symbols: {symbols}\n")

for symbol in symbols:
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        print(f"{symbol}: No tick data")
        continue

    spread = tick.ask - tick.bid
    
    print(f"--- {symbol} ---")
    print(f"Ask: {tick.ask}, Bid: {tick.bid}")
    print(f"Spread (Points): {spread}")
    
    # The logic in strategy_engine.py:
    # if spread > (target_usd * 0.3):
    is_blocked = spread > threshold
    
    print(f"Blocked by Spread Protection? {is_blocked} ({spread} > {threshold})")
    
    # Also check volatility
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 20)
    if rates is not None and len(rates) > 0:
        # Calculate recent ATR roughly (High-Low)
        tr = [r['high'] - r['low'] for r in rates]
        avg_tr = sum(tr) / len(tr)
        print(f"Approx ATR(20): {avg_tr}")

mt5.shutdown()
