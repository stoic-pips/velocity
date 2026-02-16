'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, TrendingUp, Settings } from 'lucide-react';
import clsx from 'clsx';

export const BottomNav: React.FC = () => {
    const pathname = usePathname();

    const navItems = [
        { href: '/', icon: Activity, label: 'Dash' },
        { href: '/stats', icon: TrendingUp, label: 'Stats' },
        { href: '/config', icon: Settings, label: 'Config' },
    ];

    return (
        <nav className="fixed bottom-0 left-0 right-0 bg-stoic-black border-t border-white/10 p-4 pb-6 flex justify-around items-center z-50 md:hidden">
            {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={clsx(
                            "flex flex-col items-center gap-1 transition-colors",
                            isActive ? "text-stoic-action" : "text-gray-500 hover:text-white"
                        )}
                    >
                        <Icon className="w-6 h-6" />
                        <span className="text-[10px] font-bold uppercase tracking-wider">{item.label}</span>
                    </Link>
                );
            })}
        </nav>
    );
};
