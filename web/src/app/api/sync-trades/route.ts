import { createClient } from '@/utils/supabase/server';
import { NextRequest, NextResponse } from 'next/server';

// export const runtime = 'nodejs'; // Use nodejs runtime for robust fetch handling

export const runtime = 'edge';

export async function POST(request: NextRequest) {
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    try {
        const backendUrl = process.env.NEXT_PUBLIC_API_URL + '/api/sync';
        const apiKey = process.env.NEXT_PUBLIC_API_KEY;

        // Call Python Backend
        const response = await fetch(backendUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': apiKey || '',
            },
            body: JSON.stringify({
                user_id: user.id,
                days: 30, // Default to 30 days
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            return NextResponse.json(
                { error: 'Backend sync failed', details: errorData },
                { status: response.status }
            );
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error: any) {
        console.error('Sync Error:', error);
        return NextResponse.json({ error: 'Internal Server Error', details: error.message }, { status: 500 });
    }
}
