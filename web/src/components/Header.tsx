'use client';

import React from 'react';
import { TrendingUp, Wifi, WifiOff, LogOut } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import clsx from 'clsx';

interface HeaderProps {
    mt5Connected: boolean;
    isActive: boolean;
    loading?: boolean;
}

export const Header: React.FC<HeaderProps> = ({ mt5Connected, isActive, loading }) => {
    const router = useRouter();

    const handleLogout = async () => {
        const { error } = await supabase.auth.signOut();
        if (error) {
            console.error('Error logging out:', error);
        } else {
            router.push('/login');
            router.refresh();
        }
    };

    return (
        <header className="flex justify-between items-center mb-8 pt-2">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                <TrendingUp className="text-stoic-action w-6 h-6" />
                VELOCITY
            </h1>
            <div className="flex items-center gap-3">
                {/* MT5 Connection Indicator */}
                <div className={clsx(
                    "p-1.5 rounded-lg border",
                    mt5Connected ? "border-stoic-action/30 text-stoic-action" : "border-red-500/30 text-red-400"
                )} title={mt5Connected ? 'MT5 Connected' : 'MT5 Disconnected'}>
                    {mt5Connected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
                </div>
                {/* Bot Status Badge */}
                <div className={clsx(
                    "px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-2",
                    isActive ? "bg-stoic-action/20 text-stoic-action border border-stoic-action/50" : "bg-stoic-gray text-gray-400 border border-white/10"
                )}>
                    <div className={clsx("w-2 h-2 rounded-full", isActive ? "bg-stoic-action animate-pulse" : "bg-gray-500")} />
                    {isActive ? 'Active' : 'Standby'}
                </div>
                {/* Logout */}
                <button
                    onClick={handleLogout}
                    disabled={loading}
                    className="p-2 rounded-lg bg-stoic-gray border border-white/5 text-gray-400 hover:text-white hover:bg-stoic-gray/80 transition-all active:scale-95"
                    title="Sign Out"
                >
                    <LogOut className="w-5 h-5" />
                </button>
            </div>
        </header>
    );
};
