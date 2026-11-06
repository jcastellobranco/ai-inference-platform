# Public-release readiness checklist

## Architecture
- [x] Monorepo frontend/backend layout
- [x] PostgreSQL tenant RLS policies and transaction-scoped tenant context
- [x] Dedicated worker role and lease fencing scaffold
- [ ] Full API-to-worker-to-database integration demonstrated
- [ ] Schema migrations managed by versioned migration tool
- [ ] Replace development JWT generator with OIDC/JWKS
- [ ] Add tenant quotas, rate limits and retention

## Verification
- [ ] GitHub Actions backend tests confirmed green
- [ ] GitHub Actions frontend build confirmed green
- [ ] Real PostgreSQL tenant-isolation tests confirmed green
- [ ] Docker Compose smoke test confirmed green
- [ ] Load test: concurrent workers and lease recovery
- [ ] Dependency and container vulnerability scans
- [ ] Secret scan and repository history review

## Documentation
- [x] Security threat model
- [x] Worker design and known limitations
- [ ] One-command reproducible demo with screenshots
- [ ] Architecture decision records
- [ ] API contract and OpenAPI examples
- [ ] Deployment runbook and incident troubleshooting

Do not represent this repository as production-ready until the unchecked items are addressed and verified.
