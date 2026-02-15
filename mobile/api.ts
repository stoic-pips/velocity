/**
 * Dunam Velocity – API Client
 * Pre-configured axios instance with base URL and API key header.
 */

import axios from "axios";

// ── Configuration ──────────────────────────────────────────────────────────
// In a real app these come from react-native-config or expo-constants.
const API_BASE_URL = "http://YOUR_SERVER_IP:8000";
const API_KEY = "change-me-to-a-strong-random-string";

// ── Axios Instance ─────────────────────────────────────────────────────────
const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10_000,
    headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
    },
});

// ── Typed Helpers ──────────────────────────────────────────────────────────

export interface ToggleResponse {
    status: string;
    running: boolean;
    error?: string;
}

export interface StatusResponse {
    bot: { running: boolean; mt5_connected: boolean };
    account: Record<string, unknown> | null;
    positions: Array<Record<string, unknown>>;
    position_count: number;
}

/** Start the bot (connects MT5 + launches scalper). */
export const startBot = () =>
    api.post<ToggleResponse>("/api/start");

/** Stop the bot. */
export const stopBot = () =>
    api.post<ToggleResponse>("/api/stop");

/** Fetch current bot status. */
export const getStatus = () =>
    api.get<StatusResponse>("/api/status");

/** Open a new position. */
export const openTrade = (symbol: string, lot: number, direction: "BUY" | "SELL") =>
    api.post("/api/open", { symbol, lot, direction });

/** Close a position by ticket, or all if omitted. */
export const closeTrade = (ticket?: number) =>
    api.post("/api/close", ticket ? { ticket } : {});

/** Close all open positions. */
export const closeAll = () =>
    api.post("/api/close-all");

/** Manually trigger a small-profit check. */
export const checkSmallProfit = (threshold?: number) =>
    api.post("/api/small-profit", threshold ? { threshold } : {});

export default api;
