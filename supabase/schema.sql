create extension if not exists pgcrypto;

create table if not exists public.decision_runs (
  id uuid primary key default gen_random_uuid(),
  asset text not null,
  snapshot_time_utc timestamptz not null,
  reference_price numeric,
  reference_price_date date,
  price_source text,
  overall_signal text not null,
  total_score integer not null,
  action text not null,
  market_bias text not null,
  conviction text not null,
  position_size_bucket text not null,
  signal_output jsonb not null,
  signal_story jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists decision_runs_asset_snapshot_idx
  on public.decision_runs (asset, snapshot_time_utc desc);

create table if not exists public.latest_asset_state (
  asset text primary key,
  snapshot_time_utc timestamptz not null,
  reference_price numeric,
  reference_price_date date,
  price_source text,
  overall_signal text not null,
  total_score integer not null,
  action text not null,
  market_bias text not null,
  conviction text not null,
  position_size_bucket text not null,
  signal_output jsonb not null,
  signal_story jsonb not null,
  updated_at timestamptz not null default now()
);

create table if not exists public.site_cache (
  cache_key text primary key,
  payload jsonb not null,
  source text not null,
  refresh_interval_minutes integer not null,
  updated_at timestamptz not null default now()
);

create table if not exists public.news_events (
  id uuid primary key default gen_random_uuid(),
  asset text not null,
  currency_id text,
  news_id text not null,
  release_time_ms bigint not null,
  release_time_utc timestamptz not null,
  bucket_open_ms_4h bigint not null,
  bucket_open_utc_4h timestamptz not null,
  title text not null,
  source_link text,
  original_link text,
  category integer,
  category_label text,
  author text,
  nick_name text,
  tags jsonb not null default '[]'::jsonb,
  matched_currencies jsonb not null default '[]'::jsonb,
  feature_image text,
  impression_count bigint not null default 0,
  like_count bigint not null default 0,
  reply_count bigint not null default 0,
  retweet_count bigint not null default 0,
  importance_score numeric not null default 0,
  is_major boolean not null default false,
  raw_payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (asset, news_id)
);

alter table public.decision_runs enable row level security;
alter table public.latest_asset_state enable row level security;
alter table public.site_cache enable row level security;
alter table public.news_events enable row level security;

drop policy if exists "public can read latest asset state" on public.latest_asset_state;
create policy "public can read latest asset state"
  on public.latest_asset_state
  for select
  to anon, authenticated
  using (true);

drop policy if exists "public can read site cache" on public.site_cache;
create policy "public can read site cache"
  on public.site_cache
  for select
  to anon, authenticated
  using (true);

drop policy if exists "public can read news events" on public.news_events;
create policy "public can read news events"
  on public.news_events
  for select
  to anon, authenticated
  using (true);

drop policy if exists "service role manages decision runs" on public.decision_runs;
create policy "service role manages decision runs"
  on public.decision_runs
  for all
  to service_role
  using (true)
  with check (true);

drop policy if exists "service role manages latest asset state" on public.latest_asset_state;
create policy "service role manages latest asset state"
  on public.latest_asset_state
  for all
  to service_role
  using (true)
  with check (true);

drop policy if exists "service role manages site cache" on public.site_cache;
create policy "service role manages site cache"
  on public.site_cache
  for all
  to service_role
  using (true)
  with check (true);

drop policy if exists "service role manages news events" on public.news_events;
create policy "service role manages news events"
  on public.news_events
  for all
  to service_role
  using (true)
  with check (true);
