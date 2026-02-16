'use client';

import React from 'react';
import { PageContainer } from '@/components/PageContainer';
import { TrendingUp, BarChart3, PieChart, ArrowUpRight, ArrowDownRight } from 'lucide-react';

export default function StatsPage() {
    return (
        <PageContainer>
            <div className="space-y-6">
                {/* Performance Overview */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-stoic-charcoal border border-white/5 rounded-2xl p-4">
                        <p className="text-gray-500 text-[10px] uppercase font-bold tracking-widest mb-1">Win Rate</p>
                        <div className="flex items-baseline gap-1">
                            <span className="text-2xl font-bold text-stoic-action">68.5</span>
                            <span className="text-xs text-gray-600">%</span>
                        </div>
                    </div>
                    <div className="bg-stoic-charcoal border border-white/5 rounded-2xl p-4">
                        <p className="text-gray-500 text-[10px] uppercase font-bold tracking-widest mb-1">Profit Factor</p>
                        <div className="flex items-baseline gap-1">
                            <span className="text-2xl font-bold text-white">1.24</span>
                        </div>
                    </div>
                </div>

                {/* Growth Chart Placeholder */}
                <div className="bg-stoic-charcoal border border-white/5 rounded-2xl p-6 relative overflow-hidden">
                    <div className="flex justify-between items-center mb-6">
                        <div className="flex items-center gap-2 text-gray-300">
                            <BarChart3 className="w-5 h-5 text-stoic-action" />
                            <h2 className="font-semibold tracking-wide">Equity Growth</h2>
                        </div>
                        <span className="text-[10px] bg-stoic-action/10 text-stoic-action px-2 py-0.5 rounded font-bold uppercase">Live</span>
                    </div>

                    <div className="h-40 flex items-end gap-1 px-2">
                        {[40, 70, 45, 90, 65, 80, 50, 85, 100, 75, 95, 110].map((h, i) => (
                            <div
                                key={i}
                                className="flex-1 bg-stoic-action/20 rounded-t-sm hover:bg-stoic-action/40 transition-colors"
                                style={{ height: `${h}%` }}
                            />
                        ))}
                    </div>
                    <div className="mt-4 pt-4 border-t border-white/5 flex justify-between text-[10px] text-gray-500 font-bold uppercase tracking-widest">
                        <span>Jan</span>
                        <span>Feb</span>
                        <span>Mar</span>
                    </div>
                </div>

                {/* Recent Trades Placeholder */}
                <div className="bg-stoic-charcoal border border-white/5 rounded-2xl p-6">
                    <div className="flex items-center gap-2 mb-6 text-gray-300">
                        <PieChart className="w-5 h-5 text-stoic-action" />
                        <h2 className="font-semibold tracking-wide">Recent History</h2>
                    </div>

                    <div className="space-y-4">
                        {[
                            { pair: 'EURUSD', type: 'BUY', profit: '+12.40', time: '2m ago', win: true },
                            { pair: 'GBPUSD', type: 'SELL', profit: '-4.20', time: '15m ago', win: false },
                            { pair: 'USDJPY', type: 'BUY', profit: '+8.15', time: '1h ago', win: true },
                        ].map((trade, i) => (
                            <div key={i} className="flex items-center justify-between group">
                                <div className="flex items-center gap-3">
                                    <div className={`p-2 rounded-lg ${trade.win ? 'bg-stoic-action/10' : 'bg-stoic-danger/10'}`}>
                                        {trade.win ? <ArrowUpRight className="w-4 h-4 text-stoic-action" /> : <ArrowDownRight className="w-4 h-4 text-stoic-danger" />}
                                    </div>
                                    <div>
                                        <p className="text-sm font-bold text-white">{trade.pair}</p>
                                        <p className="text-[10px] text-gray-500 font-medium">{trade.type} • {trade.time}</p>
                                    </div>
                                </div>
                                <span className={`text-sm font-bold tabular-nums ${trade.win ? 'text-stoic-action' : 'text-stoic-danger'}`}>
                                    {trade.profit}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </PageContainer>
    );
}
