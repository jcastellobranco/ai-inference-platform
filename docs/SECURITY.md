# Tenant isolation threat model

## Assets and boundaries

Tenant prompts and jobs must not be accessible to other tenants. Browsers and request bodies are untrusted. The backend validates JWT signatures, issuer, audience, expiry and tenant UUID, and derives tenant context exclusively from verified claims.

## Database enforcement

PostgreSQL `FORCE ROW LEVEL SECURITY` protects the jobs table with `USING` and `WITH CHECK`. A transaction-scoped `set_config('app.tenant_id', ..., true)` avoids session-context leakage across pooled connections. The runtime role must not own protected tables or possess `BYPASSRLS`. Migrations use a separate owner role.

## Tests

`backend/tests/test_tenant_isolation.py` creates a job as tenant A, verifies it is invisible to tenant B, and verifies that tenant B cannot insert a row for tenant A. The test requires a real migrated PostgreSQL database and a non-owner role. Tests skip explicitly when the database URL is absent.

## Known gaps

- Shared HS256 signing and manual browser token entry are development-only. Use OIDC/JWKS and proper login for production.
- Committed local-development credentials must never be reused outside a local sandbox.
- Runtime role is shared by tenants: clients must never connect directly to PostgreSQL.
- Need rate limiting, audit logs, per-tenant quotas, security scanning, secret rotation and retention policies.
