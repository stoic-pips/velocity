'use client';

import React, { useEffect, useState, useRef } from 'react';
import { PageContainer } from '@/components/PageContainer';
import { getConfig, updateConfig as apiUpdateConfig, getSymbols } from '@/lib/api-client';
import { Settings, ShieldAlert, Check, X, ChevronDown, Search } from 'lucide-react';
import clsx from 'clsx';

interface ConfigUpdatePayload {
    mt5_login: number;
    mt5_password?: string;
    mt5_server?: string;
    strategy_symbols: string;
}

export default function ConfigPage() {
    const [config, setConfig] = useState<ConfigUpdatePayload>({
        mt5_login: 0,
        mt5_password: '',
        mt5_server: '',
        strategy_symbols: '',
    });
    const [availableSymbols, setAvailableSymbols] = useState<Record<string, string[]>>({});
    const [terminalStatus, setTerminalStatus] = useState({ algo_trading: true, trade_allowed: true, mt5_connected: true });
    const [loading, setLoading] = useState(false);
    const [selectionLoading, setSelectionLoading] = useState(true);
    const [showPassword, setShowPassword] = useState(false);

    // Dropdown state
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const dropdownRef = useRef<HTMLDivElement>(null);

    const fetchSymbols = async () => {
        setSelectionLoading(true);
        try {
            const symbols = await getSymbols();
            setAvailableSymbols(symbols);
        } catch (err) {
            console.error('Failed to fetch symbols:', err);
        } finally {
            setSelectionLoading(false);
        }
    };

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [data, symbols] = await Promise.all([getConfig(), getSymbols()]);

                // Also get status to check terminal health
                const statusResponse = await fetch('http://localhost:8000/api/status', {
                    headers: { 'X-API-Key': 'change-me-to-a-strong-random-string' }
                }).catch(() => null);

                const status = statusResponse ? await statusResponse.json() : null;

                if (data) {
                    setConfig({
                        mt5_login: data.mt5_login,
                        mt5_server: data.mt5_server,
                        strategy_symbols: data.strategy_symbols,
                        mt5_password: '', // Never return password via API
                    });
                }
                setAvailableSymbols(symbols);

                if (status) {
                    setTerminalStatus({
                        algo_trading: status.account?.algo_trading_enabled ?? true,
                        trade_allowed: status.account?.trade_allowed ?? true,
                        mt5_connected: status.bot?.mt5_connected ?? false
                    });
                }
            } catch (err) {
                console.error('Failed to fetch data:', err);
            } finally {
                setSelectionLoading(false);
            }
        };
        fetchData();
    }, []);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSaveConfig = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            await apiUpdateConfig({
                mt5_login: config.mt5_login,
                mt5_password: config.mt5_password || undefined,
                mt5_server: config.mt5_server || undefined,
                strategy_symbols: config.strategy_symbols,
            });
            alert('Configuration saved to backend');
            // Refresh symbols after saving credentials/reconnect
            fetchSymbols();
        } catch (err) {
            console.error('Config update error:', err);
            alert('Failed to update config');
        }
        setLoading(false);
    };

    const toggleSymbol = (symbol: string) => {
        const currentSymbols = config.strategy_symbols.split(',').map(s => s.trim()).filter(Boolean);
        let newSymbols;
        if (currentSymbols.includes(symbol)) {
            newSymbols = currentSymbols.filter(s => s !== symbol);
        } else {
            if (currentSymbols.length >= 3) {
                alert('Maximum 3 symbols allowed for optimized scalping.');
                return;
            }
            newSymbols = [...currentSymbols, symbol];
        }
        setConfig({ ...config, strategy_symbols: newSymbols.join(', ') });
    };

    const removeSymbol = (symbol: string) => {
        const currentSymbols = config.strategy_symbols.split(',').map(s => s.trim()).filter(Boolean);
        const newSymbols = currentSymbols.filter(s => s !== symbol);
        setConfig({ ...config, strategy_symbols: newSymbols.join(', ') });
    };

    const selectedSymbolsList = config.strategy_symbols.split(',').map(s => s.trim()).filter(Boolean);

    // Limit to 3 symbols (safeguard)
    if (selectedSymbolsList.length > 3) {
        // This might happen if config is corrupted or manually edited in DB
        const truncated = selectedSymbolsList.slice(0, 3).join(', ');
        if (truncated !== config.strategy_symbols) {
            setConfig({ ...config, strategy_symbols: truncated });
        }
    }

    // Flatten symbols for searching
    const allSymbolsFlat = Object.entries(availableSymbols).flatMap(([cat, syms]) =>
        syms.map(name => ({ name, category: cat }))
    );

    const filteredSymbols = allSymbolsFlat.filter(s =>
        s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.category.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <PageContainer>
            <div className="space-y-6">
                {/* Health Warning */}
                {(!terminalStatus.algo_trading || !terminalStatus.trade_allowed) && (
                    <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-4 flex items-start gap-4 animate-in fade-in slide-in-from-top-4 duration-500">
                        <div className="p-2 bg-amber-500/20 rounded-lg">
                            <ShieldAlert className="w-5 h-5 text-amber-500" />
                        </div>
                        <div className="space-y-1">
                            <h3 className="text-amber-500 text-xs font-black uppercase tracking-widest">Action Required in MT5</h3>
                            <p className="text-[10px] text-amber-200/60 leading-relaxed font-medium">
                                {!terminalStatus.algo_trading
                                    ? "Algo Trading is disabled in your MT5 Terminal. Please press the 'Algo Trading' button at the top of your terminal to allow the bot to trade."
                                    : "Trading is not allowed for this account. Check your account permissions in the MT5 terminal."}
                            </p>
                        </div>
                    </div>
                )}
                <div className="bg-stoic-charcoal border border-white/5 rounded-2xl p-6 shadow-xl shadow-black/40">
                    <div className="flex items-center gap-2 mb-6 text-gray-300">
                        <Settings className="w-5 h-5 text-stoic-action" />
                        <h2 className="font-semibold tracking-wide uppercase text-sm">Bot Configuration</h2>
                    </div>

                    <form onSubmit={handleSaveConfig} className="space-y-6">
                        {/* Watchlist Symbols Dropdown */}
                        <div className="space-y-2">
                            <div className="flex items-center justify-between px-1">
                                <label className="text-[10px] text-gray-500 uppercase font-bold tracking-widest flex items-center gap-2">
                                    Watchlist Symbols
                                    <span className={clsx("px-1.5 py-0.5 rounded text-[8px]", selectedSymbolsList.length >= 3 ? "bg-amber-500/20 text-amber-500" : "bg-stoic-action/20 text-stoic-action")}>
                                        {selectedSymbolsList.length}/3
                                    </span>
                                </label>
                                <button
                                    type="button"
                                    onClick={(e) => { e.preventDefault(); fetchSymbols(); }}
                                    className="text-[9px] text-stoic-action uppercase font-black hover:underline disabled:opacity-50"
                                    disabled={selectionLoading}
                                >
                                    {selectionLoading ? 'Updating List...' : 'Refresh Symbols'}
                                </button>
                            </div>
                            <div className="relative" ref={dropdownRef}>
                                <div
                                    onClick={() => !selectionLoading && setIsDropdownOpen(!isDropdownOpen)}
                                    className={clsx(
                                        "w-full bg-stoic-black border border-white/10 rounded-xl p-3 flex flex-wrap gap-2 min-h-[50px] cursor-pointer transition-all",
                                        isDropdownOpen ? "border-stoic-action ring-1 ring-stoic-action/20" : "hover:border-white/20"
                                    )}
                                >
                                    {selectedSymbolsList.length > 0 ? (
                                        selectedSymbolsList.map(s => (
                                            <span key={s} className="px-2 py-1 bg-stoic-action/10 text-stoic-action text-[10px] font-bold rounded-md flex items-center gap-1.5 border border-stoic-action/20">
                                                {s}
                                                <X
                                                    className="w-3 h-3 hover:text-white transition-colors cursor-pointer"
                                                    onClick={(e) => { e.stopPropagation(); removeSymbol(s); }}
                                                />
                                            </span>
                                        ))
                                    ) : (
                                        <span className="text-sm text-gray-600 self-center">
                                            {selectionLoading ? 'Loading symbols...' : 'Select symbols to monitor...'}
                                        </span>
                                    )}
                                    <ChevronDown className={clsx("absolute right-4 top-4 w-4 h-4 text-gray-500 transition-transform", isDropdownOpen && "rotate-180")} />
                                </div>

                                {isDropdownOpen && (
                                    <div className="absolute z-50 w-full mt-2 bg-stoic-charcoal border border-white/10 rounded-xl shadow-2xl shadow-black overflow-hidden flex flex-col max-h-80 animate-in fade-in slide-in-from-top-2 duration-200">
                                        <div className="p-2 border-b border-white/5 bg-stoic-black/30">
                                            <div className="relative">
                                                <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
                                                <input
                                                    autoFocus
                                                    type="text"
                                                    placeholder="Search symbols or categories..."
                                                    value={searchQuery}
                                                    onChange={(e) => setSearchQuery(e.target.value)}
                                                    className="w-full bg-stoic-black border border-white/10 rounded-lg py-2 pl-10 pr-4 text-sm text-white focus:border-stoic-action outline-none"
                                                />
                                            </div>
                                        </div>
                                        <div className="overflow-y-auto custom-scrollbar">
                                            {filteredSymbols.length > 0 ? (
                                                filteredSymbols.map(s => {
                                                    const isSelected = selectedSymbolsList.includes(s.name);
                                                    return (
                                                        <button
                                                            key={s.name}
                                                            type="button"
                                                            onClick={() => toggleSymbol(s.name)}
                                                            className={clsx(
                                                                "w-full flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors text-left",
                                                                isSelected && "bg-stoic-action/5"
                                                            )}
                                                        >
                                                            <div className="flex flex-col">
                                                                <span className={clsx("text-sm font-medium", isSelected ? "text-stoic-action" : "text-gray-300")}>{s.name}</span>
                                                                <span className="text-[9px] text-gray-600 uppercase tracking-tighter">{s.category}</span>
                                                            </div>
                                                            {isSelected && <Check className="w-4 h-4 text-stoic-action" />}
                                                        </button>
                                                    );
                                                })
                                            ) : (
                                                <div className="p-8 text-center space-y-2">
                                                    <p className="text-gray-500 text-xs italic">
                                                        {searchQuery ? "No symbols match your search." : "No symbols available."}
                                                    </p>
                                                    {!terminalStatus.mt5_connected && !searchQuery && (
                                                        <p className="text-[10px] text-amber-500/60 leading-tight">
                                                            Check your MT5 credentials and ensure the terminal is running.
                                                        </p>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* MT5 Credentials */}
                        <div className="pt-6 border-t border-white/5 space-y-4">
                            <label className="text-[10px] text-gray-500 uppercase font-bold tracking-widest px-1">MT5 Credentials</label>
                            <div className="grid gap-3">
                                <input
                                    type="text"
                                    placeholder="Broker Login ID"
                                    value={config.mt5_login === 0 ? '' : config.mt5_login}
                                    onChange={(e) => setConfig({ ...config, mt5_login: parseInt(e.target.value) || 0 })}
                                    className="w-full bg-stoic-black border border-white/10 rounded-xl p-3 text-white text-sm focus:border-stoic-action outline-none"
                                />
                                <div className="relative">
                                    <input
                                        type={showPassword ? "text" : "password"}
                                        placeholder="Account Password"
                                        value={config.mt5_password}
                                        onChange={(e) => setConfig({ ...config, mt5_password: e.target.value })}
                                        className="w-full bg-stoic-black border border-white/10 rounded-xl p-3 text-white text-sm focus:border-stoic-action outline-none pr-10"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-black text-gray-500 hover:text-white uppercase tracking-tighter"
                                    >
                                        {showPassword ? 'Hide' : 'Show'}
                                    </button>
                                </div>
                                <input
                                    type="text"
                                    placeholder="Server (e.g. MetaQuotes-Demo)"
                                    value={config.mt5_server}
                                    onChange={(e) => setConfig({ ...config, mt5_server: e.target.value })}
                                    className="w-full bg-stoic-black border border-white/10 rounded-xl p-3 text-white text-sm focus:border-stoic-action outline-none"
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-4 rounded-2xl bg-stoic-action text-black font-black uppercase tracking-widest hover:bg-stoic-action/90 shadow-xl shadow-stoic-action/20 transition-all active:scale-[0.98] mt-4"
                        >
                            {loading ? 'Processing...' : 'Sync Configuration'}
                        </button>
                    </form>
                </div>
            </div>
        </PageContainer>
    );
}
