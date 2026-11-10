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

## Service self-service

```bash
python3 scripts/scaffold_service.py my-new-service
```

Creates a sibling `my-new-service` folder with a FastAPI app, health endpoints, a minimal non-root Dockerfile, and dependency manifest. It **does not** auto-register the new service in Compose, create secrets, or claim production-ready auth. It refuses to overwrite an existing directory. Add service-specific tenant authorization, metrics, tests and CI as appropriate.

## Service contract baseline

- Health: `GET /health/live` for process liveness and `GET /health/ready` for readiness where supported.
- HTTP APIs: publish OpenAPI from FastAPI `/openapi.json`; treat breaking changes as explicit reviews.
- Security: server-validated JWT claims; do not accept tenant identity from client-controlled headers unless authenticated and authorized. Never embed passwords in source, Compose, or generated scaffolds.
- Background jobs: PostgreSQL is the durable source of truth; Redis is ephemeral and optional.
- Telemetry: record metadata and durations, never prompts, retrieved documents, API keys or tool arguments.
- Operational checks: `docker compose ... config` before `up`, smoke workflows after `up`.

## Known boundaries

The scaffold is a **starter**, not a complete production service template. The current stack still has demo auth and incomplete document ACLs; Redis Compose and cross-repository smoke tests are not yet validated end-to-end. Terraform is maintained as reference only and must not be applied without a separate, cost-aware review.
