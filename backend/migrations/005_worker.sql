-- Local development worker identity and explicit cross-tenant RLS policy.
-- Provisioned by migration owner; never use these credentials outside local dev.
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS lease_token uuid;
DO $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='platform_worker') THEN
   CREATE ROLE platform_worker LOGIN PASSWORD 'local-worker-development-only';
 END IF;
END $$;
ALTER ROLE platform_worker NOBYPASSRLS;
GRANT CONNECT ON DATABASE platform TO platform_worker;
GRANT USAGE ON SCHEMA public TO platform_worker;
GRANT SELECT, UPDATE ON jobs TO platform_worker;
DROP POLICY IF EXISTS jobs_worker_read ON jobs;
CREATE POLICY jobs_worker_read ON jobs FOR SELECT TO platform_worker USING (true);
DROP POLICY IF EXISTS jobs_worker_write ON jobs;
CREATE POLICY jobs_worker_write ON jobs FOR UPDATE TO platform_worker USING (true) WITH CHECK (true);
