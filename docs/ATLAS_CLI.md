# ATLAS self-service CLI — local-first platform contract

Generate independent service repositories from the ATLAS Golden Path without Backstage, Kubernetes, AWS, or cloud credentials.

## Create

```bash
python3 scripts/atlas.py create-service billing-api \
  --runtime fastapi --database postgres --cache redis \
  --auth jwt --observability metrics

python3 scripts/atlas.py create-service events-api \
  --runtime node --auth jwt --observability metrics

# Equivalent Make target:
make atlas-create NAME=billing-api RUNTIME=fastapi DATABASE=postgres CACHE=redis AUTH=jwt OBSERVABILITY=metrics
```

The default destination is a sibling folder next to `ai-inference-platform`. The command refuses to overwrite existing directories and does not start containers or contact cloud services. `python3 scripts/atlas.py inspect ../billing-api` prints its `atlas-service.json` manifest.

## Generated artifacts

- Python/FastAPI or Node.js HTTP API; `GET /health/live`, `GET /health/ready`
- Non-root Dockerfile and independent loopback-only Compose port binding
- Starter test, GitHub Actions CI, .gitignore/.dockerignore, README
- Optional JWT endpoint `GET /v1/me` with signature, issuer, audience, expiry, subject and tenant checks
- Optional Prometheus `GET /metrics`
- Optional `DATABASE_URL` and `REDIS_URL` environment placeholders
- Machine-readable `atlas-service.json` describing selected capabilities

## JWT configuration

For `--auth jwt`, set a unique HS256 `JWT_SECRET` of 32+ characters in an untracked `.env`. Set `JWT_ISSUER` and `JWT_AUDIENCE` to the expected identity provider values. The endpoint fails closed when secrets are missing or invalid. The template **does not issue tokens**, provide a login server, implement tenant-level row policies, or support asymmetric/JWKS key rotation. Those are separate platform services/policies to add before real deployment.

## Observability

`--observability metrics` adds a Prometheus counter and `/metrics` endpoint. This is intentionally lightweight: it does **not** include OpenTelemetry traces, distributed spans, structured access logs, cost metering, or a running Prometheus/Grafana stack. Do not expose metrics to the public internet without an appropriate gateway or network policy.

## Dependencies and cost

`--database postgres` and `--cache redis` add connection variable placeholders, **not** database migrations, ORM models, Redis client pools, or new infrastructure. The generated Compose requires those variables and will not launch until configured. This preserves service independence and avoids unnecessary services or expenses.

## Known limitations

- Generated readiness currently reflects process readiness only, not external dependency health.
- JWT example is an HS256 demonstration and needs integration with an approved identity provider.
- Generated Node Dockerfiles install dependencies at image build time, not with a pinned lockfile; add a lockfile for reproducible production builds.
- Metrics instrumentation is a starter counter, not full HTTP latency/error monitoring.
- No automatic registration in the ATLAS main Compose or production infrastructure.
- Runtime and integration tests remain pending; only source-level CI checks have been added.

The service template is a developer convenience, **not** a security certification or a production-ready IDP.
