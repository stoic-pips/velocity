-- 1. Check for unique data and migrate
-- Insert missing configs from bot_config into bot_configs
-- We assign the old config to the FIRST user found in auth.users, as bot_config lacked user_id.
INSERT INTO public.bot_configs (user_id, bot_name, is_active, risk_params, mt5_credentials, updated_at)
SELECT 
    (SELECT id FROM auth.users ORDER BY created_at LIMIT 1) as user_id,
    'Imported Bot' as bot_name,
    strategy_enabled as is_active,
    jsonb_build_object(
        'small_profit_usd', small_profit_usd,
        'max_open_positions', max_open_positions
    ) as risk_params,
    jsonb_build_object(
        'login', mt5_login,
        'server', mt5_server
    ) as mt5_credentials,
    updated_at
FROM public.bot_config
WHERE (SELECT id FROM auth.users ORDER BY created_at LIMIT 1) IS NOT NULL
ON CONFLICT (user_id) DO NOTHING;

-- 2. Drop the redundant table
DROP TABLE IF EXISTS public.bot_config;
