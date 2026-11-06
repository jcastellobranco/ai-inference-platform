-- Support bounded delayed retries without allowing arbitrary status strings.
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_status_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_status_check
CHECK (status IN ('queued','running','retrying','completed','failed'));
CREATE INDEX IF NOT EXISTS jobs_retry_ready_idx ON jobs(leased_until)
WHERE status = 'retrying';
