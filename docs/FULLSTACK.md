# Full-stack multi-tenant architecture (work in progress)

## Repository layout

- `frontend/`: React + TypeScript + Vite operations console
- `backend/`: FastAPI API with JWT claims and SQLAlchemy transaction context
- `backend/migrations/`: PostgreSQL schema and RLS policies
- `docker-compose.fullstack.yml`: local containers
- `src/inference_platform/`: separate async inference prototype

## Security model

JWTs must be signed by a trusted issuer. The API reads the tenant UUID from a validated JWT claim, never from a client-controlled header. Each transaction sets `app.tenant_id` using PostgreSQL `set_config(..., true)`. PostgreSQL FORCE RLS restricts reads and writes, including when application code accidentally omits a tenant predicate.

**Critical setup:** Run migrations using a separate migration/owner role, and use a runtime database role that does not own the jobs table and has no BYPASSRLS privilege. The supplied Compose file is a development scaffold only: it does **not** apply migrations or provision this role automatically. Running it as-is is not a complete end-to-end demo.

## Work still required before claiming production readiness

- Separate migration and runtime DB roles with least-privilege grants
- Automated provisioning, seed data and signed development JWT generation
- JWT key rotation and OIDC/JWKS verification instead of shared HS256 secret
- Backend integration tests proving cross-tenant reads/writes are rejected
- Job worker and durable queue integration
- Frontend tests, build validation and end-to-end browser tests
- Audit logs, quotas, metrics and OpenTelemetry
- Secret management and deployment hardening

The frontend token input is strictly a development convenience, not a recommended production login flow.
