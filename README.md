# ATLAS AI Platform — AI Inference Platform

Reference portfolio platform for tenant-isolated, authenticated inference jobs, RAG retrieval and optional LLM generation.

> **Not production-ready.** Local development includes demonstration credentials and shared-secret JWTs. The frontend's development token flow is not a production authentication solution.

## Stack and features

- **Frontend:** React 19, TypeScript, Vite
- **API:** FastAPI, JWT authentication, PostgreSQL 17 and row-level security (RLS)
- **Jobs:** PostgreSQL-backed durable queue, separate worker, `SKIP LOCKED`, fencing tokens and bounded retries
- **Knowledge:** separate RAG service with pgvector hybrid retrieval
- **Evaluation:** separate HTTP evaluation service
- **Generation:** extractive by default; optional OpenAI-compatible chat-completions provider with numbered citations
- **Tracing:** job-result stage timings for retrieval, generation and evaluation (not queue wait or UI polling)

**Local-first policy:** AWS/Terraform is documentation-only and is not deployed. See [ATLAS local operating guide](docs/LOCAL_FIRST_ATLAS.md) for cost-free setup, optional Redis, repository boundaries, and later verification.

## ATLAS self-service CLI

Generate a standalone service with optional JWT authentication, Prometheus metrics, PostgreSQL/Redis client integration, dependency-aware readiness checks and file-backed JWT secrets:

```bash
python3 scripts/atlas.py create-service billing-api --runtime fastapi --database postgres --cache redis --auth jwt --observability metrics
```

For Node.js use `--runtime node`. The generated service includes Compose, CI, starter tests, health endpoints and a machine-readable manifest. See [ATLAS CLI guide](docs/ATLAS_CLI.md) for security guarantees and known gaps.

## Developer golden paths (local, no cloud)

Use `make init` to create untracked local configuration and a Redis secret without overwriting existing values; then edit `.env` and run `make doctor`. Start with `make up`, `make up-rag`, `make up-agent`, or `make up-redis` depending on the services you need. Use `make config-redis` to validate the full Compose configuration without starting containers.

Use the complete Golden Path with `make atlas-create NAME=my-service RUNTIME=fastapi AUTH=jwt OBSERVABILITY=metrics` or `python3 scripts/atlas.py create-service events-api --runtime node --auth jwt --observability metrics`. Run `make init` inside each generated service before Compose. The older `make new-service` remains a minimal skeleton for compatibility. Use `python3 scripts/atlas.py validate ../my-service` or `python3 scripts/atlas.py catalog --root ..` to inspect generated service contracts.

See [Developer Experience and Golden Paths](docs/DEVELOPER_EXPERIENCE.md).

## Prerequisites

- Git, Docker Engine and Docker Compose plugin
- Enough disk and RAM for PostgreSQL, pgvector and the sentence-transformers embedding model
- For the RAG/evaluation stack: clone the three repositories shown below; for the optional agent integration, also clone Multi-Agent and MCP
- Optional: Python and Node.js for running backend/frontend outside containers

## Quick start — integrated stack

```bash
mkdir -p ~/Projects/ai-platform
cd ~/Projects/ai-platform
git clone https://github.com/jcastellobranco/ai-inference-platform.git
git clone https://github.com/jcastellobranco/rag-document-intelligence.git
git clone https://github.com/jcastellobranco/llm-evaluation-observability.git
cd ai-inference-platform
cp .env.example .env
```

**Edit `.env` before starting:** replace the four placeholder secrets (`JWT_SECRET`, `RAG_DB_OWNER_PASSWORD`, `RAG_API_KEY`, `EVAL_API_KEY`) with distinct random values. `JWT_SECRET` must be at least 32 characters. Do not commit the populated file.

```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml up -d --build
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml ps
```

Frontend: http://127.0.0.1:8080

The integrated stack includes the API, worker, RAG and evaluation service. On the first RAG request, embedding-model weights may need to download.

### Validate the real service-to-service workflow

```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml \
  --profile smoke run --rm integration-smoke
```

A successful run prints `SUCCESS: RAG ingestion -> PostgreSQL job -> worker -> evaluation API`. This smoke test is **not** run by standard CI. It exercises real container HTTP integration, not the correctness of optional external LLM responses.

## Optional Multi-Agent + MCP integration

The React frontend now includes a **Multi-Agent** workspace for task submission, status, MCP tool outputs and execution traces. ATLAS can enqueue `POST /v1/agent/jobs` through its existing JWT/tenant-bound API, PostgreSQL queue and worker. The worker calls the private Multi-Agent HTTP API, which invokes a **real MCP stdio tool**. The default agent planner is deterministic/offline, and the end-to-end integration is **not yet verified by a running Compose smoke test**.

Clone `multi-agent-orchestration` and `mcp-tool-platform` alongside the three repositories above. Add a unique `ATLAS_AGENT_SERVICE_KEY` of at least 32 characters to `.env`, then run:

```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml -f docker-compose.agents.yml up -d --build
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml -f docker-compose.agents.yml --profile smoke run --rm agent-smoke
```

See [agent integration setup and architecture](docs/AGENT_INTEGRATION.md) for the full procedure and limitations.

## Local observability: Grafana + Prometheus

The sibling [LLM Evaluation & Observability](https://github.com/jcastellobranco/llm-evaluation-observability)
repository provides the **evaluation API, Prometheus scrape configuration and
provisioned Grafana dashboard**. This inference repository starts everything
together through an optional Docker Compose overlay.

Ensure the five repositories are cloned as siblings and updated on `main`.
From `ai-inference-platform`:

```bash
make init                  # preserves .env; generates Grafana password if missing
make config-observability
make up-observability      # full stack, RAG, agents, MCP, Redis, Prometheus, Grafana
make ps-observability
```

Grafana: **http://127.0.0.1:3000** (default username `admin`; read
`GRAFANA_ADMIN_PASSWORD` from your untracked `.env` locally).
Prometheus targets: **http://127.0.0.1:9090/targets**. Dashboards **ATLAS · Local observability**, **ATLAS · RAG & Worker**, and
**ATLAS · Container logs** are provisioned under the **ATLAS** folder. Generate some API and evaluation
traffic and allow at least two scrape intervals (30+ seconds) before expecting
nonzero rate charts.

```bash
make logs-observability
make down-observability  # preserves PostgreSQL and monitoring volumes
```

Both UIs bind only to loopback, not public interfaces. Prometheus scrapes
`backend:8000/metrics/`, `evaluation:8000/metrics/`, `rag:8000/metrics/`, and
`worker:9101/metrics` over the private Compose network. Loki and Grafana Alloy
collect service-specific Docker logs using a restricted Docker API proxy.
Update the RAG and evaluation sibling repositories before rebuilding. Agent
telemetry delivery is still optional; its chart can be empty.

To inspect a container's logs in Grafana, open **Explore → ATLAS Loki** and
query `{platform="atlas",service="worker"}` (replace `worker` with `rag`,
`backend`, etc.). Logs are retained for seven days. Never include prompts,
documents or credentials in log messages; the collector cannot guarantee
redaction. The Docker socket proxy is restricted to read-only API operations
but remains sensitive on a shared Docker daemon.

## Minimal stack (without RAG/evaluation)

```bash
cd ai-inference-platform
docker compose -f docker-compose.fullstack.yml up -d --build
```

This starts the frontend, FastAPI, PostgreSQL and worker, without the optional RAG and evaluation services. `JWT_SECRET` still must be configured.

## Authentication and API usage

The API requires a **valid development JWT** for tenant-bound endpoints. Do not assume an unauthenticated curl request to `/v1/jobs` will work. See [full-stack development notes](docs/FULLSTACK.md) and the repository's developer-token script for the supported token-generation workflow.

Core endpoints:

| Endpoint | Purpose |
| --- | --- |
| `POST /v1/jobs` | Submit a regular inference job |
| `GET /v1/jobs` | List authenticated tenant jobs |
| `GET /v1/jobs/{id}` | Inspect job status and results |
| `POST /v1/rag/jobs` | Submit a document-grounded RAG job |
| `POST /v1/knowledge/search` | Search tenant-bound documents through the authenticated backend |

For document ingestion, use the authenticated knowledge API or the [integrated smoke test](docs/INTEGRATED_LOCAL_DEMO.md), which demonstrates a full ingest → job → retrieval → evaluation cycle.

## Optional LLM generation

Default mode is extractive, not a generated answer. To enable an OpenAI-compatible provider, set these values in your local `.env`:

```dotenv
RAG_GENERATION_ENABLED=true
GENERATION_API_URL=https://api.openai.com/v1
GENERATION_API_KEY=your-private-provider-key
GENERATION_MODEL=gpt-4.1-mini
GENERATION_MAX_OUTPUT_TOKENS=500
```

Recreate the worker after changing its environment:

```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml \
  up -d --build --force-recreate worker
```

The provider may incur API usage charges; a ChatGPT subscription does not automatically include API credits. Citation-format checks are **not** proof of factual accuracy.

## Tests, logs and updates

```bash
# Frontend unit tests and build (requires Node/npm)
cd frontend
npm ci
npm test
npm run build
cd ..

# Integrated service logs
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml \
  logs -f backend worker rag evaluation

# Update local source (run in ai-inference-platform)
git pull origin main
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml \
  up -d --build --force-recreate backend worker frontend

# Stop containers without deleting persistent volumes
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml down
```

Backend tests run in GitHub Actions against PostgreSQL. Inspect `.github/workflows/` for the exact CI invocation and database prerequisites before running them manually.

**Do not run `docker compose down -v` unless you explicitly intend to delete local PostgreSQL data.**

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Compose reports missing environment variables | Copy `.env.example` and replace placeholders |
| JWT rejected / 401 | Verify token signature, issuer, audience and tenant claims |
| Knowledge request rejected / 403 | Check the tenant UUID matches the RAG deployment's configured tenant |
| Worker jobs do not complete | Inspect `worker` logs, DB migrations, lease/retry status and RAG connectivity |
| First RAG request is slow | Embedding model may be loading or downloading |
| Frontend not reachable | Check `docker compose ... ps` and host port 8080 |
| Provider fails | Check worker-side generation settings, key and provider error logs (never paste keys) |

## Architecture and engineering rules

```text
React frontend -> FastAPI JWT -> PostgreSQL jobs + RLS -> durable worker
                                                       |
                                       RAG pgvector hybrid HTTP API
                                                       |
                                      optional grounded LLM generation
                                                       |
                                         Evaluation HTTP API
                                                       |
                                           job results and citations
```

The RAG HTTP service is **single-tenant per deployment**, bound to `RAG_SERVICE_TENANT_ID`. Workers use separate DB credentials; the browser never receives service credentials.

- [Integrated Docker Compose guide](docs/INTEGRATED_LOCAL_DEMO.md)
- [Full-stack notes](docs/FULLSTACK.md)
- [RAG and evaluation contracts](docs/RAG_EVALUATION_INTEGRATION.md)
- [Agent development rules](AGENTS.md)

Normal CI does not validate the entire cross-repository Compose topology. External model factuality is not guaranteed.
