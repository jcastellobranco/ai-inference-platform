# AI Inference Platform

Multi-tenant FastAPI + React reference platform for authenticated, durable background jobs, PostgreSQL RLS and worker retries.

## What works

- JWT-authenticated job APIs: `POST /v1/jobs`, `GET /v1/jobs`, `GET /v1/jobs/{id}`.
- PostgreSQL 17 transactional queues, dedicated non-owner runtime role, row-level security and separate worker account.
- `SKIP LOCKED` leasing, fencing tokens, retry backoff and bounded retry attempts.
- React + TypeScript dashboard and Docker Compose full-stack example.
- `POST /v1/rag/jobs` for tenant-bound document questions with optional reference-based evaluation.
- Optional OpenAI-compatible chat-completions provider requiring numbered citations from retrieved evidence. Default execution remains extractive, and the original plain inference task is a deterministic uppercase demo.
- GitHub Actions tests the package, backend against PostgreSQL and frontend build. Multi-service HTTP contracts have unit tests; full multi-container execution is available as a separate smoke test.

## Three-service architecture

```
React / API client -> FastAPI JWT -> PostgreSQL jobs + RLS -> durable worker
                                                         |
                                           RAG pgvector hybrid HTTP API
                                                         |
                                          optional grounded LLM generation
                                                         |
                                            Evaluation HTTP API (optional)
                                                         |
                                            job result + cited sources
```

The RAG HTTP service is **single-tenant per deployment**. It must only be reached for the UUID configured in `RAG_SERVICE_TENANT_ID`. A separate server configuration is needed for another tenant. Worker access to all queued jobs uses a dedicated service role; browser clients never get worker credentials.

## Local demo

- [Original full-stack](docs/FULLSTACK.md)
- [Integrated three-service Docker Compose](docs/INTEGRATED_LOCAL_DEMO.md)
- [Service contracts and constraints](docs/RAG_EVALUATION_INTEGRATION.md)

## Verification status and limitations

The cross-repository Docker Compose environment requires sibling checkouts of `rag-document-intelligence` and `llm-evaluation-observability`. Run the explicit `integration-smoke` service to validate actual HTTP calls across containers; that smoke test is **not part of the standard CI**. Unit tests mock model responses; they do **not** prove factual grounding or correct operation of a real LLM provider.

This is a reference portfolio project and is **not production-ready**.
