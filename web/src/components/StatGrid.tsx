'use client';

import React from 'react';
import { useStats } from '@/hooks/useStats';
import { RefreshCw, TrendingUp, TrendingDown, Minus, Clock, BarChart3, Activity } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import clsx from 'clsx';

interface StatGridProps {
    userId: string;
}

export function StatGrid({ userId }: StatGridProps) {
    const { stats, isLoading, isSyncing, syncTrades, trend } = useStats(userId);

    if (isLoading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
                {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-40 bg-gray-800 rounded-xl" />
                ))}
            </div>
        );
    }

    if (!stats) return null;

    // Helper for trend data (mocked for sparkline as we don't store historical floating pnl in hook state history)
    // In a real app we'd keep a history array. For now, showing a flat line or simple mock.
    const sparklineData = [
        { value: stats.total_profit * 0.9 },
        { value: stats.total_profit * 0.95 },
        { value: stats.total_profit },
        { value: stats.total_profit + stats.floating_pnl }
    ];

    return (
        <div className="space-y-6">
            {/* Header with Sync */}
            <div className="flex justify-between items-center bg-stoic-charcoal p-4 rounded-xl border border-white/5">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <Activity className="text-stoic-action w-5 h-5" />
                    Live Statistics
                </h2>
                <button
                    onClick={syncTrades}
                    disabled={isSyncing}
                    className="flex items-center gap-2 px-4 py-2 bg-stoic-black rounded-lg text-xs font-bold uppercase tracking-wider text-stoic-action hover:bg-stoic-black/80 transition-all border border-stoic-action/20"
                >
                    <RefreshCw className={clsx("w-4 h-4", isSyncing && "animate-spin")} />
                    {isSyncing ? 'Syncing...' : 'Sync Trades'}
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Card 1: Visual Net Profit */}
                <div className="bg-stoic-charcoal p-6 rounded-2xl border border-white/5 relative overflow-hidden group">
                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <p className="text-xs text-gray-500 uppercase font-bold tracking-widest">Net Equity P/L</p>
                            <div className={clsx("text-2xl font-bold mt-1 flex items-center gap-2",
                                (stats.total_profit + stats.floating_pnl) >= 0 ? "text-stoic-action" : "text-stoic-danger"
                            )}>
                                ${(stats.total_profit + stats.floating_pnl).toFixed(2)}
                                {trend === 'up' && <TrendingUp className="w-4 h-4" />}
                                {trend === 'down' && <TrendingDown className="w-4 h-4" />}
                            </div>
                        </div>
                    </div>
                    <div className="h-16 w-full opacity-30 group-hover:opacity-50 transition-opacity">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={sparklineData}>
                                <Line
                                    type="monotone"
                                    dataKey="value"
                                    stroke={(stats.total_profit + stats.floating_pnl) >= 0 ? "#00FF41" : "#FF3B30"}
                                    strokeWidth={2}
                                    dot={false}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Card 2: Today's P/L */}
                <div className="bg-stoic-charcoal p-6 rounded-2xl border border-white/5 relative">
                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <p className="text-xs text-gray-500 uppercase font-bold tracking-widest flex items-center gap-2">
                                Today's P/L
                                <span className="relative flex h-2 w-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-stoic-action opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-stoic-action"></span>
                                </span>
                            </p>
                            <div className={clsx("text-2xl font-bold mt-1",
                                stats.today_profit >= 0 ? "text-stoic-action" : "text-stoic-danger"
                            )}>
                                ${stats.today_profit.toFixed(2)}
                            </div>
                        </div>
                    </div>
                    <p className="text-xs text-gray-400 mt-4">
                        Real-time updates active
                    </p>
                </div>

                {/* Card 3: Win Rate */}
                <div className="bg-stoic-charcoal p-6 rounded-2xl border border-white/5 flex items-center justify-between">
                    <div>
                        <p className="text-xs text-gray-500 uppercase font-bold tracking-widest">Win Rate</p>
                        <div className="text-3xl font-bold text-white mt-1">
                            {stats.win_rate_pct.toFixed(1)}%
                        </div>
                        <div className="text-xs text-gray-400 mt-2 flex items-center gap-2">
                            <span className="text-stoic-action">{stats.buy_count} Buys</span>
                            <span className="text-gray-600">|</span>
                            <span className="text-stoic-danger">{stats.sell_count} Sells</span>
                        </div>
                    </div>
                    <div className="relative w-16 h-16">
                        <svg className="w-full h-full transform -rotate-90">
                            <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="4" fill="transparent" className="text-gray-800" />
                            <circle
                                cx="32" cy="32" r="28"
                                stroke="currentColor"
                                strokeWidth="4"
                                fill="transparent"
                                className="text-stoic-action"
                                strokeDasharray={175.9}
                                strokeDashoffset={175.9 - (175.9 * stats.win_rate_pct) / 100}
                            />
                        </svg>
                    </div>
                </div>

                {/* Card 4: Detailed Stats */}
                <div className="bg-stoic-charcoal p-6 rounded-2xl border border-white/5 space-y-4">
                    <div>
                        <p className="text-xs text-gray-500 uppercase font-bold tracking-widest mb-1">Avg Hold Time</p>
                        <div className="flex items-center gap-2 text-white font-medium">
                            <Clock className="w-4 h-4 text-gray-400" />
                            {Math.floor(stats.avg_hold_seconds / 3600)}h {Math.floor((stats.avg_hold_seconds % 3600) / 60)}m
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/10">
                        <div>
                            <p className="text-[10px] text-gray-500 uppercase font-bold">Best Pair</p>
                            <p className="text-stoic-action font-bold">{stats.best_pair || '—'}</p>
                        </div>
                        <div>
                            <p className="text-[10px] text-gray-500 uppercase font-bold">Worst Pair</p>
                            <p className="text-stoic-danger font-bold">{stats.worst_pair || '—'}</p>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}
