# ATLAS CLI — Golden Path local-first v1

ATLAS provides a developer self-service platform without Backstage, Kubernetes, AWS or cloud provisioning. Independent microservices are created with standard capabilities and a local developer workflow. This is a complete **local v1 Golden Path**, not a production security certification.

## Create

    python3 scripts/atlas.py create-service payments-api \
      --runtime fastapi --database postgres --cache redis \
      --auth jwt --observability metrics

    python3 scripts/atlas.py create-service events-api \
      --runtime node --auth jwt --observability metrics

    make atlas-create NAME=payments-api RUNTIME=fastapi DATABASE=postgres CACHE=redis AUTH=jwt OBSERVABILITY=metrics

Choose --destination to override the default sibling-directory location. Names must be lowercase kebab-case. Services are staged in a temporary directory and published by rename. Existing directories are not overwritten, and a temporary local lock prevents concurrent ATLAS CLI generations for the same name.

## Run

    cd ../payments-api
    make init
    # Edit local .env and provide DATABASE_URL/REDIS_URL when selected.
    make config
    make up
    curl http://127.0.0.1:8000/health/live
    curl http://127.0.0.1:8000/health/ready
    make logs
    make down

make init creates an untracked .env and (for JWT-enabled services) an untracked random JWT secret only if missing. Configure external dependencies yourself: enabling --database postgres / --cache redis adds client packages and **real readiness probes**, but not running servers, database schemas, migrations, Redis pools, or credentials. Readiness returns HTTP 503 when a selected dependency cannot be reached. Liveness does not depend on external services.

By default, Compose binds to the local loopback address only. To run multiple projects, set ATLAS_HOST_PORT=8001 (or another free port) in the generated .env.

## Generated contracts

| Capability | Python FastAPI | Node.js 22 |
| --- | --- | --- |
| Container | Python 3.12 non-root | Node 22 Alpine non-root |
| Health | /health/live and /health/ready | /health/live and /health/ready |
| API | Native /openapi.json | Starter /openapi.json |
| JWT | PyJWT, HS256 | jose, HS256 |
| Metrics | Prometheus client | prom-client |
| Database | psycopg v3 if selected | pg if selected |
| Cache | redis-py if selected | redis if selected |
| Quality | pytest and CI | node:test and CI |
| Local operations | Makefile, standalone Compose | Makefile, standalone Compose |
| Discovery | atlas-service.json | atlas-service.json |

### Security and tenant boundaries

JWT-enabled templates expose authenticated GET /v1/me and validate signature, issuer, audience, expiration, subject and tenant_id. They read their HS256 secret from **/run/secrets/atlas_jwt_secret**, mounted as a Docker Compose file secret. Local bootstrap generates a 48-byte-class URL-safe random value under .secrets/atlas_jwt_secret, never stores it in code or interpolated environment variables, and never overwrites a user-defined secret.

The default per-service local secrets are deliberately independent. To validate tokens from one trusted local issuer, configure the appropriate shared secret securely; production services should prefer approved OIDC/JWKS identity providers, key rotation and per-tenant authorization/RLS. The generator does **not** implement login, token issuance, tenant resource isolation or API route-level permission policies.

### Observability

Optional /metrics exposes request count by method, route template and status and a request duration histogram. Labels are deliberately bounded; no JWTs, prompts, payloads, tenants or document content are included in labels. This starter does not include OpenTelemetry traces or dashboards. Metrics should not be publicly exposed without appropriate network policies.

## Catalog, inspect, validate

    python3 scripts/atlas.py inspect ../payments-api
    python3 scripts/atlas.py validate ../payments-api
    python3 scripts/atlas.py catalog --root ..

inspect prints the selected capabilities. validate performs **static** contract checks and returns non-zero on failure. catalog discovers sibling services using their manifests and shows valid/invalid status without a server, API registry or cloud dependencies.

## Verification

GitHub Actions verifies the generator contract and a matrix of generated minimal/full Python and Node services, dependency installation, Compose syntax, health tests and JWT behavior. The matrix does not provision PostgreSQL, Redis or cloud infrastructure. For manual local checks use make init, make config and make test after installing the generated dependencies.

## Scope boundary

This v1 is designed for independent local development, not certified production deployment. It does not create database tables, migrations, tenant policies, a secrets manager, an identity provider, complete distributed tracing, automatic registration in the central ATLAS Compose, or a service web portal. Node dependencies currently install without a committed lockfile; add one and use npm ci for reproducible production builds.

Future optional milestones: OIDC/JWKS, tenant authorization/RLS, OpenTelemetry end-to-end, runtime service discovery, infrastructure provisioning, and a developer portal only when justified by actual team demand.
