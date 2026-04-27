# Supabase Setup

This project uses Supabase as the storage and read layer for:

- historical decision-engine runs
- latest BTC/ETH state for the frontend
- website-ready cached JSON payloads

In the current hosted setup, Supabase automation refreshes the website-facing signal data roughly every 14 to 16 minutes.

The Python decision engine still runs in this repo. Supabase stores the outputs.

## What We Are Building

Roughly every 14 to 16 minutes, a server-side runner should:

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
- use the hosted Supabase automation cadence that refreshes roughly every 14 to 16 minutes

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
- `quick_trade_inputs_btc`
- `quick_trade_inputs_eth`

Useful for:

- homepage sections
- market context cards
- frontend-friendly combined payloads

## Step 4: Run the Existing Publisher

The current publishing flow is already wired in:

- [scripts/daily_signals.py](/c:/Users/elias/Desktop/narralytica_v2/scripts/daily_signals.py)

If `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are present, this script will:

1. Generate BTC and ETH outputs
2. Insert rows into `decision_runs`
3. Upsert rows into `latest_asset_state`
4. Upsert cache payloads into `site_cache`

Website news is handled in the website repo through its own news API routes. It is not part of the active backend publishing path here.

## Step 5: Frontend Read Pattern

Recommended frontend reads:

1. Read `latest_asset_state`
   Use this for live per-asset decision cards and current signal state.

2. Read `site_cache` where `cache_key = 'engine_summary'`
   Use this for lightweight cross-asset summaries.

3. Read `site_cache` where `cache_key = 'market_overview'`
   Use this for fear/greed, ETF metrics, futures context, and sector context.

4. Read `decision_runs`
   Use this later for signal history, audits, and historical chart pages.

5. Read `site_cache` where `cache_key = 'quick_trade_inputs_btc'` or `quick_trade_inputs_eth`
   Use this for Quick Trade inputs and tactical setup reads.

Website news should be documented and consumed from the website repo, since that is where the live news APIs are used.

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

## Recommended Scheduling

The active hosted setup uses Supabase automation and refreshes website-facing signal data roughly every 14 to 16 minutes.

That is the cadence the website should expect for:

- `latest_asset_state`
- `site_cache` overview payloads
- `site_cache` quick-trade payloads

## Next Best Step

After the database is created, the next step is:

1. add real Supabase credentials to `.env`
2. run the daily runner once
3. verify data appears in the core tables
4. wire the frontend to read `latest_asset_state` and `site_cache`
