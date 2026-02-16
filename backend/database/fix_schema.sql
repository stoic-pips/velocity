-- SQL Migration to fix 'bot_status' table schema
-- Run this in your Supabase SQL Editor: https://supabase.com/dashboard/project/_/sql

-- 1. Ensure 'user_id' column exists
ALTER TABLE public.bot_status 
ADD COLUMN IF NOT EXISTS user_id TEXT;

-- 2. Populate 'user_id' for existing rows if needed (or default to 'velocity_bot')
UPDATE public.bot_status 
SET user_id = 'velocity_bot' 
WHERE user_id IS NULL;

-- 3. Ensure 'user_id' is NOT NULL so it can be a primary key
ALTER TABLE public.bot_status 
ALTER COLUMN user_id SET NOT NULL;

-- 4. Add other missing columns
ALTER TABLE public.bot_status 
ADD COLUMN IF NOT EXISTS is_running BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS open_pl NUMERIC DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS position_count INTEGER DEFAULT 0;

-- 5. Drop old primary key constraint if it exists (might be on 'id')
ALTER TABLE public.bot_status 
DROP CONSTRAINT IF EXISTS bot_status_pkey;

-- 6. Set 'user_id' as the new primary key
ALTER TABLE public.bot_status 
ADD PRIMARY KEY (user_id);

-- Optional: If you had 'running' column, you might want to drop it later, but keeping it is fine.
-- ALTER TABLE public.bot_status DROP COLUMN IF EXISTS running;
