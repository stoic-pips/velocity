import sys
import os
import MetaTrader5 as mt5

# Initialize MT5
if not mt5.initialize():
    print("MT5 Init failed")
    sys.exit(1)

# Check all symbols
all_symbols = mt5.symbols_get()
if not all_symbols:
    print("Failed to get symbols")
    mt5.shutdown()
    sys.exit(1)

# Filter for anything with 'Volatility' or 'Index' or '75'
print(f"Total symbols found: {len(all_symbols)}")
print("\n--- Matching Symbols ---")
matches = [s.name for s in all_symbols if "Volatility" in s.name or "Index" in s.name or "75" in s.name]
matches.sort()

for s in matches:
    print(s)

mt5.shutdown()
