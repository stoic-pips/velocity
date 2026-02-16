import MetaTrader5 as mt5
import os
from dotenv import load_dotenv

# Load from backend/.env
load_dotenv("backend/.env")

login_str = os.getenv("MT5_LOGIN", "0")
login = int(login_str) if login_str else 0
password = os.getenv("MT5_PASSWORD", "")
server = os.getenv("MT5_SERVER", "")
path = os.getenv("MT5_PATH", "")

print(f"Attempting to connect with:")
print(f"Login: {login}")
print(f"Server: {server}")
print(f"Path: {path}")

init_kwargs = {}
if login: init_kwargs["login"] = login
if password: init_kwargs["password"] = password
if server: init_kwargs["server"] = server
if path: init_kwargs["path"] = path

if not mt5.initialize(**init_kwargs):
    print(f"mt5.initialize() failed, error code = {mt5.last_error()}")
    quit()

print("Connect successful")
account_info = mt5.account_info()
if account_info:
    print(f"Connected to account: {account_info.login}")
    print(f"Server: {account_info.server}")
else:
    print("Failed to get account info")

symbols = mt5.symbols_get()
if symbols:
    print(f"Fetched {len(symbols)} symbols")
    for s in symbols[:5]:
        print(f" - {s.name}")
else:
    print("No symbols fetched")

mt5.shutdown()
