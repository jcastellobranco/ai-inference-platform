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

ATLAS can now enqueue `POST /v1/agent/jobs` through its existing JWT/tenant-bound API, PostgreSQL queue and worker. The worker calls the private Multi-Agent HTTP API, which invokes a **real MCP stdio tool**. The default agent planner is deterministic/offline, and the end-to-end integration is **not yet verified by a running Compose smoke test**.

Clone `multi-agent-orchestration` and `mcp-tool-platform` alongside the three repositories above. Add a unique `ATLAS_AGENT_SERVICE_KEY` of at least 32 characters to `.env`, then run:

```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml -f docker-compose.agents.yml up -d --build
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml -f docker-compose.agents.yml --profile smoke run --rm agent-smoke
```

See [agent integration setup and architecture](docs/AGENT_INTEGRATION.md) for the full procedure and limitations.

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
