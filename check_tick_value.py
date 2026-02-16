import sys
import os
import MetaTrader5 as mt5

# Initialize MT5
if not mt5.initialize():
    print("MT5 Init failed")
    sys.exit(1)

import time
symbols = ["Volatility 75 Index", "Volatility 75 (1s) Index", "EURUSD"]

print(f"{'Symbol':<20} | {'Bid':<10} | {'Ask':<10} | {'Spread':<10} | {'TickVal':<10} | {'Spread($)':<10}")
print("-" * 90)

for symbol in symbols:
    # Ensure selected
    if not mt5.symbol_select(symbol, True):
        print(f"{symbol:<20} | Failed to select")
        continue

    time.sleep(1) # Wait for tick data

    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    
    if not info or not tick:
        print(f"{symbol:<20} | No info/tick")
        continue

    spread = tick.ask - tick.bid
    tick_value = info.trade_tick_value
    
    # Calculate cost for 0.01 lot (or min volume)
    volume = 0.01
    if info.volume_min > volume:
        volume = info.volume_min
        
    # Spread cost in account currency (USD)
    # Formula usually: Spread_points * Tick_Value * Volume? 
    # Or Spread_price * Tick_Value / Tick_Size * Volume?
    # Tick_Value is usually per 1 lot per 1 tick (point).
    
    # Let's try: spread_cost = spread_points * (tick_value / tick_size) * volume? 
    # Actually: profit = (close - open) * tick_value / tick_size * volume
    # So spread_cost = spread * (tick_value / point) * volume
    
    # But MT5 'spread' in symbol_info is in points (integers). 
    # tick.ask - tick.bid is in PRICE units.
    
    spread_price = tick.ask - tick.bid
    
    # Cost = spread_price * (tick_value / point) * volume?
    # No, tick_value is "value of one tick". One tick = point.
    # So Cost = (spread_price / point) * tick_value * volume
    
    cost = (spread_price / info.point) * tick_value * volume
    
    print(f"{symbol:<20} | {tick.bid:<10.5f} | {tick.ask:<10.5f} | {spread_price:<10.5f} | {tick_value:<10.5f} | {cost:<10.5f}")

mt5.shutdown()
