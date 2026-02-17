-- 1. Create system_logs table
create table if not exists public.system_logs (
    id bigint primary key generated always as identity,
    user_id uuid, -- Link to auth.users if available, else just text if using loose coupling
    event text not null,
    level text default 'info', -- info, warning, error, critical
    details jsonb default '{}'::jsonb,
    created_at timestamptz default now()
);

-- Enable RLS for system_logs
alter table public.system_logs enable row level security;
create policy "Enable all access for anon" on public.system_logs for all using (true) with check (true);
alter publication supabase_realtime add table system_logs;

-- 2. Expand bot_configs to hold all RuntimeConfig fields (if not using jsonb for everything)
-- We will rely on the existing 'risk_params' and 'mt5_credentials' JSONB columns for nested data,
-- or add specific columns if we want stricter schema.
-- Let's ensure top-level params exist.
alter table public.bot_configs add column if not exists strategy_symbols text;
alter table public.bot_configs add column if not exists strategy_timeframe text default 'M1';
alter table public.bot_configs add column if not exists strategy_check_interval float default 0.5;

-- Volatility params can go into a new JSONB column or separate columns.
alter table public.bot_configs add column if not exists volatility_params jsonb default '{
    "enabled": true,
    "min_atr": 0.0001,
    "avg_period": 20,
    "extreme_threshold": 2.5
}'::jsonb;
