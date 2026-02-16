"""
Dunam Velocity – MT5 Manager (Singleton)
Thread-safe MetaTrader 5 connection, order execution, and price polling.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

import MetaTrader5 as mt5

from config.settings import get_settings


class MT5Manager:
    """
    Singleton class to manage MetaTrader 5 connection and operations.
    Thread-safe storage of the connection state.
    """

    _instance: Optional["MT5Manager"] = None
    _lock: threading.Lock = threading.Lock()

    # ── Singleton ───────────────────────────────────────────────────────────

    def __new__(cls) -> "MT5Manager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._connected = False
                    cls._instance._account_info: Optional[mt5.AccountInfo] = None
                    cls._instance._api_lock = threading.RLock()
        return cls._instance

    @classmethod
    def instance(cls) -> MT5Manager:
        """Explicit accessor for the singleton instance."""
        return cls()

    # ── Connection ──────────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        """Whether the MT5 terminal is currently connected."""
        return self._connected

    def connect(self) -> bool:
        """
        Initialize and log in to the MT5 terminal.
        Returns True on success, False on failure.
        """
        with self._api_lock:
            settings = get_settings()
            init_kwargs: dict = {}

            if settings.mt5_path:
                init_kwargs["path"] = settings.mt5_path
            if settings.mt5_login:
                init_kwargs["login"] = settings.mt5_login
            if settings.mt5_password:
                init_kwargs["password"] = settings.mt5_password
            if settings.mt5_server:
                init_kwargs["server"] = settings.mt5_server

            if not mt5.initialize(**init_kwargs):
                print(f"[MT5] initialize() failed – {mt5.last_error()}")
                self._connected = False
                return False

            account = mt5.account_info()
            if account:
                print(
                    f"[MT5] Connected → {account.server}  "
                    f"Login: {account.login}  "
                    f"Balance: {account.balance} {account.currency}"
                )
            self._connected = True
            return True

    def disconnect(self) -> None:
        """Cleanly shut down the MT5 connection."""
        with self._api_lock:
            mt5.shutdown()
            self._connected = False
            print("[MT5] Shutdown complete.")

    # ── Account & Position Info ─────────────────────────────────────────────

    def get_account_info(self) -> Optional[dict]:
        """Return key account metrics, or None if not connected."""
        with self._api_lock:
            info = mt5.account_info()
            if info is None:
                return None
            return {
                "login": info.login,
                "server": info.server,
                "balance": info.balance,
                "equity": info.equity,
                "margin": info.margin,
                "free_margin": info.margin_free,
                "profit": info.profit,
                "currency": info.currency,
                "trade_allowed": info.trade_allowed,
                "algo_trading_enabled": mt5.terminal_info().trade_allowed if mt5.terminal_info() else False
            }

    def get_positions(self) -> list[dict]:
        """Return all open positions as a list of dicts."""
        with self._api_lock:
            positions = mt5.positions_get()
            if positions is None:
                return []
            return [
                {
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                    "volume": p.volume,
                    "open_price": p.price_open,
                    "current_price": p.price_current,
                    "profit": p.profit,
                    "swap": p.swap,
                    "comment": p.comment,
                }
                for p in positions
            ]

    def get_tick(self, symbol: str) -> Optional[dict]:
        """Return the current bid/ask for a symbol."""
        with self._api_lock:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            return {
                "symbol": symbol,
                "bid": tick.bid,
                "ask": tick.ask,
                "time": tick.time,
            }

    def get_categorized_symbols(self) -> dict[str, list[str]]:
        """
        Fetch all available symbols and group them by folder (category).
        e.g. {'Forex Major': ['EURUSD', ...], 'Synthetic Indices': [...]}
        """
        with self._api_lock:
            symbols = mt5.symbols_get()
            if symbols is None:
                print("[MT5] symbols_get() returned None. Check connection.")
                return {}
            
            if not symbols:
                print("[MT5] symbols_get() returned an empty list.")
                return {}

            print(f"[MT5] Fetched {len(symbols)} symbols from terminal.")
            categories: dict[str, list[str]] = {}
            for s in symbols:
                # Path format is usually 'Folder\Subfolder\Symbol'
                parts = s.path.split("\\")
                category = parts[0] if parts else "Other"
                
                if category not in categories:
                    categories[category] = []
                categories[category].append(s.name)
            
            # Sort categories and symbols for better UX
            sorted_categories = dict(sorted(categories.items()))
            for cat in sorted_categories:
                sorted_categories[cat].sort()
                
            return sorted_categories

    def get_filling_mode(self, symbol: str) -> int:
        """
        Detect the supported filling mode for a symbol.
        Returns mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, or mt5.ORDER_FILLING_RETURN.
        """
        with self._api_lock:
            info = mt5.symbol_info(symbol)
            if info is None:
                return mt5.ORDER_FILLING_IOC
            
            # Check for FOK (Fill or Kill)
            # Standard bits: SYMBOL_FILLING_FOK (1), SYMBOL_FILLING_IOC (2)
            if info.filling_mode & 1:
                return mt5.ORDER_FILLING_FOK
            # Check for IOC (Immediate or Cancel)
            elif info.filling_mode & 2:
                return mt5.ORDER_FILLING_IOC
            
            return mt5.ORDER_FILLING_RETURN

    # ── Order Execution ─────────────────────────────────────────────────────

    def open_order(
        self,
        symbol: str,
        lot: float,
        direction: str,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "Velocity",
    ) -> dict:
        """
        Send a market order.
        direction: "BUY" | "SELL"
        Returns a result dict with 'success' key.
        """
        with self._api_lock:
            settings = get_settings()

            # ── Validations ────────────────────────────────────────────────────
            current_positions = self.get_positions()
            if len(current_positions) >= settings.max_open_positions:
                return {"success": False, "error": f"Max open positions ({settings.max_open_positions}) reached"}

            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return {"success": False, "error": f"Symbol '{symbol}' not found"}
            if not symbol_info.visible:
                mt5.symbol_select(symbol, True)

            # ── Build request ──────────────────────────────────────────────────
            order_type = mt5.ORDER_TYPE_BUY if direction.upper() == "BUY" else mt5.ORDER_TYPE_SELL
            tick = mt5.symbol_info_tick(symbol)
            price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": order_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 20,
                "magic": 234000,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": self.get_filling_mode(symbol),
            }

            result = mt5.order_send(request)
            if result is None:
                return {"success": False, "error": str(mt5.last_error())}
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {
                    "success": False,
                    "error": f"Order failed – retcode {result.retcode}: {result.comment}",
                }

            return {
                "success": True,
                "ticket": result.order,
                "price": result.price,
                "volume": result.volume,
            }

    def close_order(self, ticket: int) -> dict:
        """Close a single position by ticket number."""
        with self._api_lock:
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                return {"success": False, "error": f"Position {ticket} not found"}

            pos = positions[0]
            close_type = (
                mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            )
            tick = mt5.symbol_info_tick(pos.symbol)
            price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": "Velocity close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": self.get_filling_mode(pos.symbol),
            }

            result = mt5.order_send(request)
            if result is None:
                return {"success": False, "error": str(mt5.last_error())}
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {
                    "success": False,
                    "error": f"Close failed – retcode {result.retcode}: {result.comment}",
                }

            return {"success": True, "ticket": ticket, "close_price": result.price}

    def close_all_orders(self) -> dict:
        """Close every open position. Returns a summary."""
        positions = self.get_positions()
        if not positions:
            return {"closed": 0, "errors": []}

        closed: int = 0
        errors: list[dict] = []

        for pos in positions:
            res = self.close_order(pos["ticket"])
            if res["success"]:
                closed += 1
            else:
                errors.append({"ticket": pos["ticket"], "error": res["error"]})

        return {"closed": closed, "errors": errors}
