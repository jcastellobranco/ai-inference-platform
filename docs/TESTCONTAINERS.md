# PostgreSQL integration testing with Testcontainers

The tests in `tests/test_postgres_rls_integration.py` launch a real PostgreSQL 17 container, run all `backend/migrations/00*.sql` in order as the database owner, then connect with the separate `platform_runtime` and `platform_worker` roles.

They verify migrations, RLS tenant isolation, blocked cross-tenant INSERT/UPDATE, transaction-local tenant context on a reused connection, and worker-specific cross-tenant read policy.

## Local

Requires a running Docker daemon (Docker Desktop, Linux Docker Engine, or WSL Docker integration). The test suite does not require AWS.

```bash
python -m pip install -e '.[dev]'
python -m pytest tests/test_postgres_rls_integration.py -q
```

GitHub Actions runs these tests on Ubuntu runners with Docker available. Keep these tests in the integration tier: they are slower than unit tests, but validate actual PostgreSQL behavior rather than mocks.

**Security:** migration 002/005 role passwords are strictly local development fixtures, never production credentials. Tests do not require or create cloud resources.
