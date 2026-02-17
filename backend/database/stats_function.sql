-- PostgreSQL Function: calculate_user_stats

create or replace function public.calculate_user_stats(p_user_id uuid)
returns json
language plpgsql
security definer
as $$
declare
  v_timezone text;
  v_stats json;
begin
  -- 1. Fetch user timezone, default to UTC if not set
  select timezone into v_timezone
  from public.bot_configs
  where user_id = p_user_id;
  
  if v_timezone is null then
    v_timezone := 'UTC';
  end if;

  -- 2. Calculate stats
  with trade_summary as (
    select
      coalesce(sum(profit), 0) as total_profit,
      coalesce(sum(case when closed_at >= (now() at time zone v_timezone)::date then profit else 0 end), 0) as today_profit,
      count(*) as total_trades,
      count(*) filter (where is_success) as success_trades,
      count(*) filter (where direction = 'buy') as buy_count,
      count(*) filter (where direction = 'sell') as sell_count,
      avg(extract(epoch from (closed_at - opened_at))) as avg_hold_seconds
    from public.trade_logs
    where user_id = p_user_id
  ),
  pair_performance as (
    select symbol, sum(profit) as pair_profit
    from public.trade_logs
    where user_id = p_user_id
    group by symbol
  ),
  best_worst as (
    select
      (select symbol from pair_performance order by pair_profit desc limit 1) as best_pair,
      (select symbol from pair_performance order by pair_profit asc limit 1) as worst_pair
  ),
  active_summary as (
    select coalesce(sum(floating_pnl), 0) as floating_pnl
    from public.active_trades
    where user_id = p_user_id
  )
  select json_build_object(
    'total_profit', t.total_profit,
    'today_profit', t.today_profit,
    'win_rate_pct', case when t.total_trades > 0 then (t.success_trades::numeric / t.total_trades) * 100 else 0 end,
    'total_trades', t.total_trades,
    'buy_count', t.buy_count,
    'sell_count', t.sell_count,
    'avg_hold_seconds', coalesce(t.avg_hold_seconds, 0),
    'best_pair', bw.best_pair,
    'worst_pair', bw.worst_pair,
    'floating_pnl', a.floating_pnl
  ) into v_stats
  from trade_summary t
  cross join best_worst bw
  cross join active_summary a;

  return v_stats;
end;
$$;

-- Grant access
grant execute on function public.calculate_user_stats(uuid) to authenticated;
