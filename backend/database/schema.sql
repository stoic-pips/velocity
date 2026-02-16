-- 1. Bot Status Table
create table if not exists public.bot_status (
    id text primary key default 'velocity_bot',
    running boolean default false,
    mt5_connected boolean default false,
    updated_at timestamptz default now()
);

-- Initialize default status
insert into public.bot_status (id, running, mt5_connected)
values ('velocity_bot', false, false)
on conflict (id) do nothing;

-- 2. Bot Configuration Table
create table if not exists public.bot_config (
    id int primary key generated always as identity,
    mt5_login text,
    mt5_password text,
    mt5_server text,
    small_profit_usd float default 2.0,
    max_lot_size float default 1.0,
    max_open_positions int default 10,
    strategy_enabled boolean default true,
    updated_at timestamptz default now()
);

-- Initialize default config row
insert into public.bot_config (mt5_login, small_profit_usd, max_lot_size, max_open_positions)
values ('', 2.0, 1.0, 10)
on conflict do nothing; 
-- Note: conflict handling on identity columns is tricky, usually we just check exists
-- but for a simple setup, this script is idempotent-ish.

-- 3. Trades History
create table if not exists public.trades (
    id bigint primary key generated always as identity,
    ticket bigint,
    symbol text,
    type text, -- 'BUY' or 'SELL'
    volume float,
    open_price float,
    close_price float,
    profit float,
    action text, -- 'small_profit_close', 'manual_close', etc.
    threshold float, -- logic threshold used if applicable
    positions_closed int,
    timestamp timestamptz default now()
);

-- 4. Account Snapshots (Balance/Equity curve)
create table if not exists public.account_snapshots (
    id bigint primary key generated always as identity,
    login bigint,
    server text,
    currency text,
    balance float,
    equity float,
    margin float,
    free_margin float,
    profit float,
    timestamp timestamptz default now()
);

-- 5. Open Positions (Synced real-time)
create table if not exists public.positions (
    ticket bigint primary key,
    symbol text,
    type text, -- 'BUY' or 'SELL'
    volume float,
    open_price float,
    current_price float,
    profit float,
    sl float,
    tp float,
    updated_at timestamptz default now()
);

-- RLS Policies (Allow inherited access or public for now since it's a single user bot)
alter table public.bot_status enable row level security;
alter table public.bot_config enable row level security;
alter table public.trades enable row level security;
alter table public.account_snapshots enable row level security;
alter table public.positions enable row level security;

-- Open access policy (RESTRICT THIS IN PRODUCTION)
create policy "Enable all access for anon" on public.bot_status for all using (true) with check (true);
create policy "Enable all access for anon" on public.bot_config for all using (true) with check (true);
create policy "Enable all access for anon" on public.trades for all using (true) with check (true);
create policy "Enable all access for anon" on public.account_snapshots for all using (true) with check (true);
create policy "Enable all access for anon" on public.positions for all using (true) with check (true);

-- Enable Realtime for these tables (Must run AFTER tables are created)
alter publication supabase_realtime add table bot_status;
alter publication supabase_realtime add table bot_config;
alter publication supabase_realtime add table trades;
alter publication supabase_realtime add table account_snapshots;
alter publication supabase_realtime add table positions;
