import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/lib/supabase';
import { RealtimeChannel } from '@supabase/supabase-js';

export interface StatsState {
    total_profit: number;
    today_profit: number;
    win_rate_pct: number;
    total_trades: number;
    buy_count: number;
    sell_count: number;
    avg_hold_seconds: number;
    best_pair: string | null;
    worst_pair: string | null;
    floating_pnl: number;
    // Computed fields
    account_balance?: number; // Base balance + floating PnL (approximation)
}

export interface UseStatsResult {
    stats: StatsState | null;
    isLoading: boolean;
    isSyncing: boolean;
    error: string | null;
    syncTrades: () => Promise<void>;
    trend: 'up' | 'down' | 'neutral';
}

export function useStats(userId: string): UseStatsResult {
    const [stats, setStats] = useState<StatsState | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSyncing, setIsSyncing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [trend, setTrend] = useState<'up' | 'down' | 'neutral'>('neutral');

    // Fetch initial stats via RPC
    const fetchStats = useCallback(async () => {
        try {
            if (!userId) return;

            const { data, error } = await supabase.rpc('calculate_user_stats', {
                p_user_id: userId,
            });

            if (error) throw error;

            setStats((prev) => {
                // If we have previous stats, we can check trend on floating PnL
                if (prev && data) {
                    const prevFloat = prev.floating_pnl;
                    const newFloat = data.floating_pnl;
                    if (newFloat > prevFloat) setTrend('up');
                    else if (newFloat < prevFloat) setTrend('down');
                    else setTrend('neutral');
                }
                return data as StatsState;
            });
        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, [userId]);

    // Sync trades with backend
    const syncTrades = async () => {
        setIsSyncing(true);
        try {
            const res = await fetch('/api/sync-trades', {
                method: 'POST',
            });

            if (!res.ok) {
                throw new Error('Sync failed');
            }

            await fetchStats(); // Refresh stats after sync
        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsSyncing(false);
        }
    };

    useEffect(() => {
        if (!userId) return;

        fetchStats();

        // Real-time Subscriptions
        const channels: RealtimeChannel[] = [];

        // 1. Subscribe to trade_logs (historical) -> Full Refresh
        const tradeLogsChannel = supabase
            .channel('trade_logs_changes')
            .on(
                'postgres_changes',
                {
                    event: '*',
                    schema: 'public',
                    table: 'trade_logs',
                    filter: `user_id=eq.${userId}`,
                },
                () => {
                    fetchStats();
                }
            )
            .subscribe();
        channels.push(tradeLogsChannel);

        // 2. Subscribe to active_trades (live) -> Update Floating PnL only
        const activeTradesChannel = supabase
            .channel('active_trades_changes')
            .on(
                'postgres_changes',
                {
                    event: '*',
                    schema: 'public',
                    table: 'active_trades',
                    filter: `user_id=eq.${userId}`,
                },
                (payload) => {
                    // Re-fetch stats to represent accurate total PnL
                    // Optimization: Apply delta locally if payload info is sufficient, 
                    // but RPC is safer for aggregations.
                    fetchStats();
                }
            )
            .subscribe();
        channels.push(activeTradesChannel);

        return () => {
            channels.forEach((channel) => supabase.removeChannel(channel));
        };
    }, [userId, fetchStats]);

    return {
        stats,
        isLoading,
        isSyncing,
        error,
        syncTrades,
        trend,
    };
}
