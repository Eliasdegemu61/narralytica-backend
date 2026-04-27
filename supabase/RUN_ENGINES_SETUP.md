# Run Engines Setup

This project now has a Supabase Edge Function orchestrator that replaces running two separate Python cron jobs.

## What it does

Every run executes in this order:

1. Core daily signal refresh
2. Quick trade input refresh for BTC and ETH

Both steps write directly into Supabase.

## Required secrets

Set these in Supabase Edge Function secrets:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SOSO_API_KEY`
- `RUN_ENGINES_SECRET`

## Deploy

From the repo root:

```bash
supabase functions deploy run-engines --no-verify-jwt
```

`supabase/config.toml` already marks `run-engines` with `verify_jwt = false`, so the scheduler can call it directly. The function still checks `x-run-engines-secret` when `RUN_ENGINES_SECRET` is configured.

## Schedule

Run the SQL in:

`supabase/run_engines_schedule.sql`

Before running it, replace:

- `<your-project-ref>`
- `<your-run-engines-secret>`

## Freshness model

The quick-trade payloads still publish:

- `refresh_interval_minutes = 15`
- `client_max_data_age_minutes = 10`
- `client_refresh_buffer_minutes = 1`

So the client rule remains:

- if the snapshot is older than 10 minutes, do not open a new quick trade
- wait until the next scheduled refresh plus the 1-minute buffer
