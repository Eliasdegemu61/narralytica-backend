create extension if not exists pg_cron;
create extension if not exists pg_net;

-- Replace the project ref and secret placeholders before running this.
-- This schedules one Supabase-native orchestrator every 15 minutes.
-- The Edge Function itself runs core signals first, then quick trade snapshots.

select cron.unschedule(jobid)
from cron.job
where jobname = 'run-engines-every-15-minutes';

select cron.schedule(
  'run-engines-every-15-minutes',
  '*/15 * * * *',
  $$
  select
    net.http_post(
      url := 'https://<your-project-ref>.supabase.co/functions/v1/run-engines',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'x-run-engines-secret', '<your-run-engines-secret>'
      ),
      body := '{}'::jsonb
    ) as request_id;
  $$
);
