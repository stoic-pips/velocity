'use client';

import React, { useEffect, useState } from 'react';
import { useRealtime } from '@/hooks/useRealtime';
import { supabase } from '@/lib/supabase';
import { Activity, Power, Settings, ShieldAlert, DollarSign, TrendingUp } from 'lucide-react';
import clsx from 'clsx';

export default function Dashboard() {
    const { botStatus, openPL } = useRealtime();
    const [isActive, setIsActive] = useState(false);
    const [config, setConfig] = useState({
        small_profit_usd: 2.0,
        max_lot_size: 1.0,
        max_open_positions: 10,
        mt5_login: '',
        mt5_password: '',
        mt5_server: '',
    });
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (botStatus) {
            setIsActive(botStatus.is_active);
        }
        const fetchConfig = async () => {
            const { data } = await supabase.from('bot_config').select('*').single();
            if (data) setConfig(data);
        };
        fetchConfig();
    }, [botStatus]);

    const toggleBot = async () => {
        setLoading(true);
        const newState = !isActive;
        setIsActive(newState); // Optimistic update

        // Call backend API or update Supabase directly if RPC/RLS allows. 
        // Assuming direct update for now as requested "Server Actions" usually implies DB update.
        const { error } = await supabase
            .from('bot_status')
            .update({ is_active: newState })
            .eq('id', 1);

        if (error) {
            console.error('Error toggling bot:', error);
            setIsActive(!newState); // Revert
        }
        setLoading(false);
    };

    const updateConfig = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        const { error } = await supabase
            .from('bot_config')
            .update(config)
            .eq('id', 1);

        if (error) alert('Failed to update config');
        else alert('Config updated successfully');
        setLoading(false);
    };

    return (
        <div className="min-h-screen bg-stoic-black text-white p-4 pb-20 font-sans selection:bg-stoic-action selection:text-black">
            {/* Header */}
            <header className="flex justify-between items-center mb-8 pt-2">
                <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                    <TrendingUp className="text-stoic-action w-6 h-6" />
                    VELOCITY
                </h1>
                <div className={clsx(
                    "px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-2",
                    isActive ? "bg-stoic-action/20 text-stoic-action border border-stoic-action/50" : "bg-stoic-gray text-gray-400 border border-white/10"
                )}>
                    <div className={clsx("w-2 h-2 rounded-full", isActive ? "bg-stoic-action animate-pulse" : "bg-gray-500")} />
                    {isActive ? 'Active' : 'Standby'}
                </div>
            </header>

            <main className="space-y-6 max-w-md mx-auto">
                {/* Core Component 1: Live Profit Card */}
                <div className="bg-stoic-charcoal border border-white/5 rounded-2xl p-6 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-50">
                        <DollarSign className="w-12 h-12 text-white/5" />
                    </div>
                    <p className="text-gray-400 text-sm font-medium uppercase tracking-widest mb-1">Open P/L</p>
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

                {/* Core Component 2: Bot Toggle */}
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
                        {loading ? 'Processing...' : (isActive ? 'System Armed' : 'System Disarmed')}
                    </div>
                </button>

                {/* Core Component 3: Risk Config Form */}
                <div className="bg-stoic-charcoal border border-white/5 rounded-2xl p-6">
                    <div className="flex items-center gap-2 mb-6 text-gray-300">
                        <Settings className="w-5 h-5" />
                        <h2 className="font-semibold tracking-wide">Risk Configuration</h2>
                    </div>

                    <form onSubmit={updateConfig} className="space-y-5">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="text-xs text-gray-500 uppercase font-bold tracking-wider">Small Profit ($)</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    value={config.small_profit_usd}
                                    onChange={(e) => setConfig({ ...config, small_profit_usd: parseFloat(e.target.value) })}
                                    className="w-full bg-stoic-black border border-white/10 rounded-lg p-3 text-white focus:border-stoic-action focus:ring-1 focus:ring-stoic-action outline-none transition-all"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs text-gray-500 uppercase font-bold tracking-wider">Max Lots</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    value={config.max_lot_size}
                                    onChange={(e) => setConfig({ ...config, max_lot_size: parseFloat(e.target.value) })}
                                    className="w-full bg-stoic-black border border-white/10 rounded-lg p-3 text-white focus:border-stoic-action focus:ring-1 focus:ring-stoic-action outline-none transition-all"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs text-gray-500 uppercase font-bold tracking-wider">Max Open Positions</label>
                            <div className="relative">
                                <input
                                    type="number"
                                    value={config.max_open_positions}
                                    onChange={(e) => setConfig({ ...config, max_open_positions: parseInt(e.target.value) })}
                                    className="w-full bg-stoic-black border border-white/10 rounded-lg p-3 text-white focus:border-stoic-action focus:ring-1 focus:ring-stoic-action outline-none transition-all"
                                />
                                <ShieldAlert className="absolute right-3 top-3 w-5 h-5 text-gray-600" />
                            </div>
                        </div>

                        <div className="space-y-2 border-t border-white/5 pt-4 mt-2">
                            <label className="text-xs text-gray-500 uppercase font-bold tracking-wider mb-2 block">MT5 Credentials</label>
                            <div className="grid gap-3">
                                <input
                                    type="text"
                                    placeholder="Login ID"
                                    value={config.mt5_login}
                                    onChange={(e) => setConfig({ ...config, mt5_login: e.target.value })}
                                    className="w-full bg-stoic-black border border-white/10 rounded-lg p-3 text-white text-sm focus:border-stoic-action outline-none"
                                />
                                <div className="relative">
                                    <input
                                        type={showPassword ? "text" : "password"}
                                        placeholder="Password"
                                        value={config.mt5_password}
                                        onChange={(e) => setConfig({ ...config, mt5_password: e.target.value })}
                                        className="w-full bg-stoic-black border border-white/10 rounded-lg p-3 text-white text-sm focus:border-stoic-action outline-none pr-10"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white text-xs font-bold uppercase"
                                    >
                                        {showPassword ? 'Hide' : 'Show'}
                                    </button>
                                </div>
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-4 rounded-xl bg-stoic-action text-black font-bold uppercase tracking-widest hover:bg-stoic-action/90 transition-colors mt-4 shadow-lg shadow-stoic-action/20"
                        >
                            {loading ? 'Saving...' : 'Save Configuration'}
                        </button>
                    </form>
                </div>
            </main>

            {/* Mobile Bottom Nav */}
            <nav className="fixed bottom-0 left-0 right-0 bg-stoic-black border-t border-white/10 p-4 pb-6 flex justify-around items-center z-50 md:hidden">
                <div className="flex flex-col items-center gap-1 text-stoic-action">
                    <Activity className="w-6 h-6" />
                    <span className="text-[10px] font-bold uppercase tracking-wider">Dash</span>
                </div>
                <div className="flex flex-col items-center gap-1 text-gray-500 hover:text-white transition-colors">
                    <TrendingUp className="w-6 h-6" />
                    <span className="text-[10px] font-bold uppercase tracking-wider">Stats</span>
                </div>
                <div className="flex flex-col items-center gap-1 text-gray-500 hover:text-white transition-colors">
                    <Settings className="w-6 h-6" />
                    <span className="text-[10px] font-bold uppercase tracking-wider">Config</span>
                </div>
            </nav>
        </div>
    );
}
