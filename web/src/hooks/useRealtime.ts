import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

export interface BotStatus {
    id: number;
    is_active?: boolean;
    running?: boolean;
    status_message: string;
    last_updated: string;
    open_pl?: number;
    position_count?: number;
}

export interface Position {
    ticket: number;
    symbol: string;
    profit: number;
    type: string;
}

export const useRealtime = () => {
    const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
    const [positions, setPositions] = useState<Position[]>([]);
    const [openPL, setOpenPL] = useState<number>(0);
    const [positionCount, setPositionCount] = useState<number>(0);

    useEffect(() => {
        // Initial fetch
        const fetchData = async () => {
            const { data: statusData } = await supabase
                .from('bot_status')
                .select('*')
                .single();
            if (statusData) {
                const status = statusData as BotStatus;
                setBotStatus({
                    ...status,
                    is_active: status.running ?? status.is_active ?? false
                });
                if (status.open_pl !== undefined) setOpenPL(status.open_pl);
                if (status.position_count !== undefined) setPositionCount(status.position_count);
            }

            const { data: positionsData } = await supabase
                .from('positions')
                .select('*');
            if (positionsData) {
                setPositions(positionsData);
                const total = positionsData.reduce((acc, pos) => acc + pos.profit, 0);
                setOpenPL(total);
            }
        };

        fetchData();

        // Realtime subscription
        const channel = supabase
            .channel('dashboard')
            .on(
                'postgres_changes',
                { event: '*', schema: 'public', table: 'bot_status' },
                (payload) => {
                    const status = payload.new as BotStatus;
                    setBotStatus({
                        ...status,
                        is_active: status.running ?? status.is_active ?? false
                    });
                    if (status.open_pl !== undefined) setOpenPL(status.open_pl);
                    if (status.position_count !== undefined) setPositionCount(status.position_count);
                }
            )
            .on(
                'postgres_changes',
                { event: '*', schema: 'public', table: 'positions' },
                () => {
                    // Simplification: Re-fetch positions on any change to ensure consistency
                    // or manually handle INSERT/UPDATE/DELETE. Re-fetching is safer for P/L sum.
                    fetchData();
                }
            )
            .subscribe();

        return () => {
            supabase.removeChannel(channel);
        };
    }, []);

    return { botStatus, positions, openPL, positionCount };
};
