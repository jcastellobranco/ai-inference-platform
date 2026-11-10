# Developer Experience and Golden Paths

ATLAS follows a **local-first** platform-as-product approach. The projects remain independent. The integration repository offers an optional paved road, not a mandatory monolith. No AWS, Terraform apply, managed Redis or paid LLM API is needed.

## Day-one developer workflow

From `ai-inference-platform`:

```bash
make init             # create untracked .env and Redis secret, without overwriting existing files
make doctor           # check Docker Compose and optional sibling repos
# Edit .env: replace example JWT/RAG/EVAL/agent secrets with unique local values.
make config-minimal   # parse Compose; does not start services
make up               # frontend, API, PostgreSQL and worker
make ps
make logs
make down             # preserves PostgreSQL volumes
```

Choose integrations only when needed:

| Goal | Check config | Start |
| --- | --- | --- |
| Core inference | `make config-minimal` | `make up` |
| RAG and evaluation | `make config-rag` | `make up-rag` |
| Agent and MCP | `make config-agent` | `make up-agent` |
| Redis planner cache and API quotas | `make config-redis` | `make up-redis` |

Optional integration checks: `make smoke-rag` and `make smoke-agent`. They require running Docker and correct secrets. The Makefile is designed for Linux/WSL/macOS with GNU Make and Python 3.

## Golden Path v1 (preferred)

Create a service with JWT, Prometheus metrics, optional PostgreSQL/Redis clients and local catalog verification:

    python3 scripts/atlas.py create-service billing-api --runtime fastapi --database postgres --cache redis --auth jwt --observability metrics
    cd ../billing-api
    make init
    make config
    make up

For Node.js use --runtime node. Use atlas validate and atlas catalog to inspect local manifests. Generated secrets live in untracked files rather than source or interpolated Compose values. Detailed contracts and limitations: [ATLAS CLI](ATLAS_CLI.md).

## Legacy minimal scaffolding

```bash
make new-service NAME=my-new-service RUNTIME=fastapi\n# or Node.js, with external dependency connection placeholders:\nmake new-service NAME=events-api RUNTIME=node POSTGRES=1 REDIS=1
```

Creates a sibling independent service with FastAPI or Node.js, health endpoints, a non-root Dockerfile, a standalone Compose file, a starter test and a CI workflow. Optional POSTGRES/REDIS flags add **connection-variable placeholders only**; they do not provision databases or Redis. The generator refuses to overwrite an existing directory. The legacy scaffold remains intentionally minimal: it does not add JWT, metrics, database clients or tracing. For those capabilities use the preferred ATLAS CLI. Authorization and distributed tracing remain future integrations.

## Service contract baseline

- Health: `GET /health/live` for process liveness and `GET /health/ready` for readiness where supported.
- HTTP APIs: publish OpenAPI from FastAPI `/openapi.json`; treat breaking changes as explicit reviews.
- Security: server-validated JWT claims; do not accept tenant identity from client-controlled headers unless authenticated and authorized. Never embed passwords in source, Compose, or generated scaffolds.
- Background jobs: PostgreSQL is the durable source of truth; Redis is ephemeral and optional.
- Telemetry: record metadata and durations, never prompts, retrieved documents, API keys or tool arguments.
- Operational checks: `docker compose ... config` before `up`, smoke workflows after `up`.

## Known boundaries

The scaffold is a **starter**, not a complete production service template. The current stack still has demo auth and incomplete document ACLs; Redis Compose and cross-repository smoke tests are not yet validated end-to-end. Terraform is maintained as reference only and must not be applied without a separate, cost-aware review.
