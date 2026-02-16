'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useRealtime } from '@/hooks/useRealtime';
import { getStatus } from '@/lib/api-client';
import { Header } from './Header';
import { BottomNav } from './BottomNav';
import { WifiOff } from 'lucide-react';

interface PageContainerProps {
    children: React.ReactNode;
}

export const PageContainer: React.FC<PageContainerProps> = ({ children }) => {
    const { botStatus } = useRealtime();
    const [isActive, setIsActive] = useState(false);
    const [mt5Connected, setMt5Connected] = useState(false);
    const [statusError, setStatusError] = useState<string | null>(null);

    const fetchBackendStatus = useCallback(async () => {
        try {
            const status = await getStatus();
            setIsActive(status.bot.running);
            setMt5Connected(status.bot.mt5_connected);
            setStatusError(null);
        } catch (err) {
            setStatusError('Backend offline');
            console.error('Backend status error:', err);
        }
    }, []);

    useEffect(() => {
        fetchBackendStatus();
        const interval = setInterval(fetchBackendStatus, 5000);

        if (botStatus) {
            setIsActive(botStatus.is_active);
        }

        return () => clearInterval(interval);
    }, [botStatus, fetchBackendStatus]);

    return (
        <div className="min-h-screen bg-stoic-black text-white p-4 pb-20 font-sans selection:bg-stoic-action selection:text-black">
            <Header mt5Connected={mt5Connected} isActive={isActive} />

            <main className="space-y-6 max-w-md mx-auto">
                {statusError && (
                    <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-red-400 text-sm font-medium flex items-center gap-2 mb-4">
                        <WifiOff className="w-4 h-4 shrink-0" />
                        {statusError} — Bot controls disabled
                    </div>
                )}
                {children}
            </main>

            <BottomNav />
        </div>
    );
};
