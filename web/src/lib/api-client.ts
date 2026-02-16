/**
 * Dunam Velocity – Backend API Client
 * Typed fetch wrapper that sends X-API-Key on every request.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';

// ── Types ──────────────────────────────────────────────────────────────────

export interface BotStatusResponse {
    bot: {
        is_active: boolean;
        mt5_connected: boolean;
    };
    account: Record<string, unknown>;
    positions: Record<string, unknown>[];
    position_count: number;
}

export interface BotActionResponse {
    status?: string;
    error?: string;
    is_active: boolean;
}

// ── Fetch Helper ───────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
    const res = await fetch(`${API_URL}${path}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': API_KEY,
            ...(options.headers || {}),
        },
    });

    if (!res.ok) {
        const body = await res.text();
        throw new Error(`API ${res.status}: ${body}`);
    }

    return res.json() as Promise<T>;
}

// ── Public Methods ─────────────────────────────────────────────────────────

/** Get full bot status including account info and positions. */
export function getStatus(): Promise<BotStatusResponse> {
    return apiFetch<BotStatusResponse>('/api/status');
}

/** Start the scalper bot. */
export function startBot(): Promise<BotActionResponse> {
    return apiFetch<BotActionResponse>('/api/start', { method: 'POST' });
}

/** Stop the scalper bot. */
export function stopBot(): Promise<BotActionResponse> {
    return apiFetch<BotActionResponse>('/api/stop', { method: 'POST' });
}

/** Close all open positions. */
export function closeAll(): Promise<BotActionResponse> {
    return apiFetch<BotActionResponse>('/api/close-all', { method: 'POST' });
}

/** Trigger a manual small-profit check. */
export function checkSmallProfit(threshold?: number): Promise<Record<string, unknown>> {
    return apiFetch('/api/small-profit', {
        method: 'POST',
        body: JSON.stringify({ threshold }),
    });
}

// ── Config ─────────────────────────────────────────────────────────────────

export interface ConfigResponse {
    mt5_login: number;
    mt5_server: string;
    strategy_symbols: string;
}

export interface ConfigUpdatePayload {
    mt5_login?: number;
    mt5_password?: string;
    mt5_server?: string;
    strategy_symbols?: string;
}

/** Get current backend configuration. */
export function getConfig(): Promise<ConfigResponse> {
    return apiFetch<ConfigResponse>('/api/config');
}

/** Update backend configuration (writes to .env and reloads). */
export function updateConfig(payload: ConfigUpdatePayload): Promise<{ status: string; updated_keys: string[] }> {
    return apiFetch('/api/config', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

// ── Trading ────────────────────────────────────────────────────────────────

export interface OpenOrderPayload {
    symbol: string;
    lot: number;
    direction: 'BUY' | 'SELL';
    sl?: number;
    tp?: number;
    comment?: string;
}

/** Open a new position. */
export function openOrder(payload: OpenOrderPayload): Promise<Record<string, unknown>> {
    return apiFetch('/api/open', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

/** Get categorized symbols from MT5. */
export async function getSymbols(): Promise<Record<string, string[]>> {
    const res = await fetch(`${API_URL}/api/symbols`, {
        headers: {
            'X-API-Key': API_KEY,
        },
    });
    if (!res.ok) throw new Error('Failed to fetch symbols');
    return res.json();
}
