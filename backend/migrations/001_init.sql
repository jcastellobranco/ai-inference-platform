-- Execute as migration owner, not the runtime application role.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS tenants (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    prompt text NOT NULL CHECK (length(prompt) BETWEEN 1 AND 8000),
    status text NOT NULL CHECK (status IN ('queued','running','completed','failed')),
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS jobs_tenant_created ON jobs(tenant_id, created_at DESC);
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS jobs_tenant_isolation ON jobs;
CREATE POLICY jobs_tenant_isolation ON jobs
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
-- IMPORTANT: the runtime role must not own tables or have BYPASSRLS.
