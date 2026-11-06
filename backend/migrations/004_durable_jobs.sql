-- Schema extension for durable background job execution.
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS result text;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS error text;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS attempts integer NOT NULL DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS leased_until timestamptz;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS worker_id text;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS finished_at timestamptz;
CREATE INDEX IF NOT EXISTS jobs_claim_idx ON jobs(status, leased_until, created_at);
-- Workers need a separate service role with deliberately scoped access.
-- Never expose worker credentials to the browser or tenant-facing API.
