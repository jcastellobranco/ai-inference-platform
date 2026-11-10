-- Local browser login: credentials and opaque sessions, separate from tenant job data.
CREATE TABLE IF NOT EXISTS app_users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  email text NOT NULL UNIQUE,
  password_hash text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (length(email) BETWEEN 3 AND 254)
);
CREATE TABLE IF NOT EXISTS browser_sessions (
  token_hash text PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
  csrf_hash text NOT NULL,
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS browser_sessions_expiry ON browser_sessions(expires_at);
GRANT SELECT, INSERT, UPDATE ON app_users TO platform_runtime;
GRANT SELECT, INSERT, DELETE ON browser_sessions TO platform_runtime;
-- User/session tables are only accessed through the auth module. Job tables
-- continue to enforce RLS with the authenticated tenant identity.

CREATE TABLE IF NOT EXISTS auth_attempts (
  identity_hash text PRIMARY KEY,
  attempts integer NOT NULL DEFAULT 0,
  window_start timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE ON auth_attempts TO platform_runtime;
