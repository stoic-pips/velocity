'use client';

import React, { useState } from 'react';
import { useRealtime } from '@/hooks/useRealtime';
import { startBot, stopBot, getStatus, closeAll } from '@/lib/api-client';
import { Power, DollarSign, ShieldAlert } from 'lucide-react';
import { PageContainer } from './PageContainer';
import clsx from 'clsx';

export default function Dashboard() {
    const { botStatus, openPL, positionCount } = useRealtime();
    const [isActive, setIsActive] = useState(false);
    const [loading, setLoading] = useState(false);

    // Initial and periodic status sync is handled by PageContainer, 
    // but we can also use useRealtime for some data.
    // We'll keep the toggleBot logic here as it's specific to the dashboard.

    const toggleBot = async () => {
        setLoading(true);
        try {
            if (isActive) {
                const res = await stopBot();
                setIsActive(res.is_active);
            } else {
                const res = await startBot();
                if (res.error) {
                    alert(`Failed to start: ${res.error}`);
                } else {
                    setIsActive(res.is_active);
                }
            }
        } catch (err) {
            console.error('Toggle bot error:', err);
            alert('Failed to reach backend API');
        }
        setLoading(false);
    };

    const handleCloseAll = async () => {
        if (!confirm('Are you sure you want to close ALL open positions immediately?')) return;
        setLoading(true);
        try {
            await closeAll();
            alert('Emergency Close-All triggered successfully.');
        } catch (err) {
            console.error('Close all error:', err);
            alert('Failed to trigger emergency close');
        }
        setLoading(false);
    };

    // Fetch initial status via API for reliability on load
    React.useEffect(() => {
        setIsActive(botStatus?.is_active ?? false);
    }, [botStatus]);

    return (
        <PageContainer>
            {/* Live Profit Card */}
            <div className="bg-stoic-charcoal border border-white/5 rounded-2xl p-6 relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-50">
                    <DollarSign className="w-12 h-12 text-white/5" />
                </div>
                <div className="flex justify-between items-center mb-1">
                    <div className="flex items-center gap-2">
                        <p className="text-gray-400 text-sm font-medium uppercase tracking-widest">Open P/L</p>
                        {isActive && (
                            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-stoic-action/10 rounded-full border border-stoic-action/20">
                                <div className="w-1.5 h-1.5 bg-stoic-action rounded-full animate-pulse shadow-[0_0_8px_rgba(0,255,65,0.8)]" />
                                <span className="text-[9px] text-stoic-action font-black uppercase tracking-tighter">Live</span>
                            </div>
                        )}
                    </div>
                    <span className="text-xs text-gray-500 tabular-nums">{positionCount} active</span>
                </div>
                <div className="flex items-baseline gap-1">
                    <span className={clsx(
                        "text-5xl font-bold tracking-tighter tabular-nums transition-colors duration-500",
                        openPL > 0 ? "text-stoic-action drop-shadow-[0_0_15px_rgba(0,255,65,0.3)]" : openPL < 0 ? "text-stoic-danger" : "text-white"
                    )}>
                        {openPL > 0 ? '+' : ''}{openPL.toFixed(2)}
                    </span>
                    <span className="text-xl text-gray-500 font-medium">USD</span>
                </div>
                <div className="mt-4 h-1 w-full bg-stoic-gray rounded-full overflow-hidden">
                    <div
                        className={clsx("h-full transition-all duration-700 ease-out", openPL > 0 ? "bg-stoic-action" : "bg-stoic-danger")}
                        style={{ width: `${Math.min(Math.abs(openPL) * 2, 100)}%`, opacity: openPL === 0 ? 0 : 1 }}
                    />
                </div>
            </div>

            {/* System Armed Toggle */}
            <button
                onClick={toggleBot}
                disabled={loading}
                className={clsx(
                    "w-full py-6 rounded-2xl font-bold text-xl uppercase tracking-widest transition-all duration-300 transform active:scale-[0.98] relative overflow-hidden group border",
                    isActive
                        ? "bg-stoic-charcoal border-stoic-action/50 text-stoic-action shadow-[0_0_30px_rgba(0,255,65,0.1)] hover:shadow-[0_0_50px_rgba(0,255,65,0.2)]"
                        : "bg-stoic-charcoal border-white/10 text-gray-400 hover:bg-stoic-gray hover:text-white"
                )}
            >
                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                    <div className="w-64 h-64 bg-white/5 rounded-full blur-3xl" />
                </div>
                <div className="relative flex items-center justify-center gap-3">
                    <Power className={clsx("w-6 h-6", isActive && "animate-pulse")} />
                    {loading ? 'Processing...' : (isActive ? 'Stop Station' : 'Start Station')}
                </div>
            </button>

            {/* Panic Button */}
            {positionCount > 0 && (
                <button
                    onClick={handleCloseAll}
                    disabled={loading}
                    className="w-full py-4 rounded-xl font-black text-xs uppercase tracking-[0.2em] border border-stoic-danger/30 text-stoic-danger bg-stoic-danger/5 hover:bg-stoic-danger/10 transition-all flex items-center justify-center gap-2 animate-in fade-in slide-in-from-bottom-2 duration-500"
                >
                    <ShieldAlert className="w-4 h-4" />
                    Emergency Close All
                </button>
            )}
        </PageContainer>
    );
}
