# Local full-stack demonstration

## Prerequisites
Docker Compose, Git, Python 3.12 (for local token creation), and PyJWT (`pip install PyJWT`).

## Start
```bash
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
docker compose -f docker-compose.fullstack.yml up --build -d
docker compose -f docker-compose.fullstack.yml ps
```

Open http://localhost:8080. Generate a 30-minute local demo token:

```bash
JWT_SECRET="$JWT_SECRET" PYTHONPATH=backend python -m scripts.dev_token --tenant 11111111-1111-4111-8111-111111111111
```

Paste the token in the developer preview UI. Submit a prompt and refresh jobs. The separate worker should process it and store a deterministic uppercase result in PostgreSQL. The UI currently displays status but not the result.

For another tenant, generate a token using `22222222-2222-4222-8222-222222222222`. Jobs from the first tenant must not appear in the second tenant's listing.

## Integration checks

```bash
pip install -r backend/requirements-dev.txt
export PYTHONPATH=backend
export TEST_DATABASE_URL='postgresql+psycopg://platform_runtime:local-development-only@localhost:5432/platform'
pytest backend/tests -q
```

The Compose database port is not published to the host. For host-side integration tests, temporarily publish a loopback-only port (e.g. `127.0.0.1:5432:5432`) in a local Compose override; never publish the development database publicly.

## Limitations

The demo uses local-only fixed database credentials, a development JWT signing secret, and a deterministic fake inference provider. It is not an internet-facing production deployment. No build or end-to-end run is claimed until verified in CI or a local Docker environment.
