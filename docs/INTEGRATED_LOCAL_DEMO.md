# Three-service integration: local Docker Compose

The repositories must be checked out alongside each other:

```
workspace/
  ai-inference-platform/
  rag-document-intelligence/
  llm-evaluation-observability/
```

The integration stack adds a second PostgreSQL instance with pgvector, a migration job, a RAG HTTP service backed by the hybrid pgvector pipeline, and an evaluation API to the existing inference stack.

Set `JWT_SECRET` (32+ random characters), `RAG_DB_OWNER_PASSWORD`, `RAG_API_KEY`, and `EVAL_API_KEY` in a local `.env` file in `ai-inference-platform`. Do not commit `.env`.

Run:

```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml up --build -d
```

The RAG server may download the configured sentence-transformers model the first time a request reaches it; plan for model storage and sufficient memory. The test-only database roles and static demo password in the RAG migrations are **not production credentials**. Use an isolated development machine.

The demo tenant is `11111111-1111-4111-8111-111111111111`. Use the existing developer JWT script to create a token for this tenant, then upload a plain-text document to `rag:8000/v1/documents` from within the Compose network or use a one-time script. Create a RAG job through the inference API `POST /v1/rag/jobs`, optionally passing `reference_answer`. Poll `GET /v1/jobs/{id}` to retrieve result, citations and evaluation metrics.

**Important:** Default mode is deterministic/extractive (the first retrieved chunk), not a generated LLM answer. For an optional OpenAI-compatible chat-completions provider, set `RAG_GENERATION_ENABLED=true`, `GENERATION_API_URL` (base ending in `/v1`), `GENERATION_API_KEY` and `GENERATION_MODEL`. The provider must return correctly numbered citations, or the job fails and retries. This is only a citation-format check; it is **not** a rigorous factuality/groundedness guarantee.

The unit CI currently validates provider contracts with test doubles and tenant-isolated pgvector integration via the RAG repository CI. This Compose topology has not been verified as a multi-container e2e run. Production deployment requires dedicated secret management, TLS/service identity, rate limits, model pinning, payload limits, network isolation and improved observability.

## Multi-container smoke test

After the stack starts, run:

```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml \
  --profile smoke run --rm integration-smoke
```

The smoke process checks service health, ingests a unique source through the **real pgvector HTTP API**, creates an authenticated inference RAG job, lets the worker retrieve and optionally generate an answer, then verifies citations and evaluation metrics through the separate evaluation service. It makes real intercontainer HTTP requests. The embedding model must be available for execution and may need to download weights on first use.

Successful execution prints `SUCCESS: RAG ingestion -> PostgreSQL job -> worker -> evaluation API`. The normal GitHub Actions tests do **not** run this containerized smoke test yet, because it requires checkout of all three separate repositories plus model weights. Until the smoke test is run successfully, the whole topology remains unverified.
