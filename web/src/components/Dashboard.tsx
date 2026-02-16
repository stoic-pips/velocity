'use client';

import React, { useState } from 'react';
import { useRealtime } from '@/hooks/useRealtime';
import { startBot, stopBot, getStatus } from '@/lib/api-client';
import { Power, DollarSign } from 'lucide-react';
import { PageContainer } from './PageContainer';
import clsx from 'clsx';

export default function Dashboard() {
    const { botStatus, openPL } = useRealtime();
    const [isActive, setIsActive] = useState(false);
    const [loading, setLoading] = useState(false);
    const [positionCount, setPositionCount] = useState(0);

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

    // React to botStatus changes from realtime
    React.useEffect(() => {
        if (botStatus) {
            setIsActive(botStatus.is_active);
        }
    }, [botStatus]);

    // Fetch initial position count once
    React.useEffect(() => {
        getStatus().then(status => setPositionCount(status.position_count)).catch(console.error);
    }, []);

    return (
        <PageContainer>
            {/* Live Profit Card */}
            <div className="bg-stoic-charcoal border border-white/5 rounded-2xl p-6 relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-50">
                    <DollarSign className="w-12 h-12 text-white/5" />
                </div>
                <div className="flex justify-between items-center mb-1">
                    <p className="text-gray-400 text-sm font-medium uppercase tracking-widest">Open P/L</p>
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
        </PageContainer>
    );
}
