# Supabase Setup

This project uses Supabase as the storage and read layer for:

- historical decision-engine runs
- latest BTC/ETH state for the frontend
- website-ready cached JSON payloads

The Python decision engine still runs in this repo. Supabase stores the outputs.

## What We Are Building

Every 20 minutes, a server-side runner should:

1. Fetch SoSoValue and other source data
2. Run the BTC and ETH decision engines
3. Save a historical record of the run
4. Update the latest BTC/ETH rows
5. Update website-ready JSON cache payloads

The frontend should then read from Supabase only.

## Important Architecture Note

Supabase does not run Python scripts directly.

That means there are two clean options:

1. Keep the Python runner in this repo and trigger it from an external scheduler
   Good options:
   - GitHub Actions cron
   - a VPS cron job
   - a small backend server

2. Rewrite the runner as a Supabase Edge Function
   This is possible later, but it is a separate migration because Edge Functions are TypeScript/Deno, not Python.

Recommended now:
- use Supabase for database + frontend reads
- keep the Python runner
- schedule the Python runner externally every 20 minutes

## Environment Variables

Create a local `.env` file from `.env.example`:

```env
SOSO_API_KEY=your_soso_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
SUPABASE_ANON_KEY=your_supabase_anon_key
```

What each one is for:

- `SOSO_API_KEY`
  Server-side only. Used by the Python runner when fetching SoSoValue data.

- `SUPABASE_URL`
  Used by the Python runner and later by the frontend.

- `SUPABASE_SERVICE_ROLE_KEY`
  Server-side only. Used by the Python runner to write data into Supabase.

- `SUPABASE_ANON_KEY`
  Frontend-safe key for reading public tables with RLS.

Never expose:

- `SOSO_API_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

## Step 1: Create the Supabase Project

In the Supabase dashboard:

1. Create a new project
2. Copy the project URL
3. Copy the `anon` key
4. Copy the `service_role` key

Put those into your local `.env`.

## Step 2: Create the Database Tables

Open the Supabase SQL Editor and run:

- [supabase/schema.sql](/c:/Users/elias/Desktop/narralytica_v2/supabase/schema.sql)

This creates:

- `decision_runs`
- `latest_asset_state`
- `news_events`
- `site_cache`

It also configures RLS so:

- the public frontend can read `latest_asset_state`
- the public frontend can read `site_cache`
- only the service role can write all tables

## Step 3: Understand What Gets Written

### `decision_runs`

This stores every engine run for history and analytics.

Useful for:

- signal history
- confidence history
- performance review
- audit trail

### `latest_asset_state`

This stores the current latest row for each asset.

You should expect rows like:

- `btc`
- `eth`

Useful for:

- homepage hero cards
- latest signal badges
- asset overview panels

### `site_cache`

This stores website-ready JSON payloads.

Current cache keys written by the runner:

- `engine_summary`
- `market_overview`

Useful for:

- homepage sections
- market context cards
- frontend-friendly combined payloads

### `news_events`

This stores individual token-filtered news items for historical website features.

Useful for:

- chart news overlays
- recent event timelines
- grouped headline history
- per-asset news review

## Step 4: Run the Existing Publisher

The current publishing flow is already wired in:

- [scripts/daily_signals.py](/c:/Users/elias/Desktop/narralytica_v2/scripts/daily_signals.py)

If `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are present, this script will:

1. Generate BTC and ETH outputs
2. Save local JSON files
3. Insert rows into `decision_runs`
4. Upsert rows into `latest_asset_state`
5. Upsert rows into `news_events`
6. Upsert cache payloads into `site_cache`

There is also a one-off backfill script for recent news history:

- [scripts/backfill_news_history.py](/c:/Users/elias/Desktop/narralytica_v2/scripts/backfill_news_history.py)

Run it with your existing Python runtime.

## Step 5: Frontend Read Pattern

Recommended frontend reads:

1. Read `latest_asset_state`
   Use this for live per-asset decision cards and current signal state.

2. Read `site_cache` where `cache_key = 'engine_summary'`
   Use this for lightweight cross-asset summaries.

3. Read `site_cache` where `cache_key = 'market_overview'`
   Use this for fear/greed, ETF metrics, futures context, and sector context.

4. Read `site_cache` where `cache_key = 'news_chart_crypto'`
   Use this for market-wide chart-ready grouped news markers.

5. Read `news_events`
   Use this for richer historical news timelines and individual event history.

6. Read `decision_runs`
   Use this later for signal history, audits, and historical chart pages.

7. Read `site_cache` where `cache_key = 'quick_trade_inputs_btc'` or `quick_trade_inputs_eth`
   Use this for Quick Trade inputs and tactical setup reads.

## Example SQL Checks

After your first publish, these should work in Supabase SQL Editor:

```sql
select asset, overall_signal, action, snapshot_time_utc
from public.latest_asset_state
order by asset;
```

```sql
select cache_key, updated_at
from public.site_cache
order by cache_key;
```

```sql
select asset, snapshot_time_utc, total_score, action
from public.decision_runs
order by snapshot_time_utc desc
limit 10;
```

```sql
select asset, news_id, release_time_utc, title, is_major
from public.news_events
order by release_time_utc desc
limit 20;
```

## Recommended Scheduling

For now, schedule the Python runner externally every 20 minutes.

Recommended first choice:

- GitHub Actions cron every 20 minutes

Why:

- easy to set secrets
- easy to review logs
- no rewrite required
- works well with this existing Python repo

Later, if you want everything deeper inside the Supabase ecosystem, we can migrate the runner to an Edge Function.

## Next Best Step

After the database is created, the next step is:

1. add real Supabase credentials to `.env`
2. run the daily runner once
3. verify data appears in the three tables
4. wire the frontend to read `latest_asset_state` and `site_cache`
