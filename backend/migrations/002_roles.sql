-- Run with database owner privileges. App role is NOT the table owner.
DO $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='platform_runtime') THEN
   CREATE ROLE platform_runtime LOGIN PASSWORD 'local-development-only';
 END IF;
END $$;
ALTER ROLE platform_runtime NOBYPASSRLS;
GRANT CONNECT ON DATABASE platform TO platform_runtime;
GRANT USAGE ON SCHEMA public TO platform_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON jobs TO platform_runtime;
GRANT SELECT ON tenants TO platform_runtime;
-- No CREATE on public and no ownership of tenant data tables.
