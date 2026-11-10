# ATLAS — local-first operating guide

## Goal and cost policy
ATLAS is a collection of **independent portfolio projects**. Integration is optional. The primary supported demonstration target is **local Docker Compose**. The Terraform/AWS repository is a reference implementation only: **do not run terraform apply, trigger deployment workflows, or create cloud resources**. There is no requirement to purchase managed Redis, RDS, ECS, LLM credits or GPU instances.

## Repository roles
- `ai-inference-platform`: React frontend, FastAPI/JWT, tenant-bound PostgreSQL RLS jobs, worker, optional service composition
- `rag-document-intelligence`: document ingestion, hybrid retrieval, pgvector
- `multi-agent-orchestration`: LangGraph, deterministic planner and optional LLM planner, MCP bridge, guardrails and Redis planner cache
- `mcp-tool-platform`: scope-gated tools and optional redacted audit hook
- `llm-evaluation-observability`: answer/retrieval evaluation, authenticated in-memory agent telemetry
- `slm-finetuning-lab`: opt-in local LoRA training
- `atlas-infrastructure`: **unapplied** Terraform reference

## Developer self-service
Run `make init`, configure `.env`, then `make doctor`. Use `make config-minimal` or `make config-redis` to check Compose before starting services. See [Developer Experience](DEVELOPER_EXPERIENCE.md) for golden paths and service scaffolding.\n\n## Start locally
Clone the sibling repositories in one directory. In `ai-inference-platform` copy `.env.example` to `.env`, replace placeholder secrets with unique values, and never commit `.env`. For the basic stack:

```bash
docker compose -f docker-compose.fullstack.yml up -d --build
```

For RAG + evaluation:
```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml up -d --build
```

For agents + MCP + optional Redis cache and distributed quotas:
```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml \
  -f docker-compose.agents.yml -f docker-compose.redis.yml up -d --build
```

The Redis overlay reads its password from the untracked `.secrets/redis_password` file (created by `make init`), not from a Compose-interpolated password. Configure a separate `ATLAS_CACHE_HMAC_KEY` of at least 32 characters in `.env`. Redis is ephemeral and must not be used for durable job state. PostgreSQL remains the durable job queue. If Redis is unavailable, agent cache is bypassed but authenticated API requests with rate limiting enabled fail closed (503).

The agent's optional telemetry endpoint uses HTTPS only; local Compose HTTP evaluation does **not** enable agent telemetry delivery by default. Evaluation endpoints are independently available, but operational telemetry integration requires an HTTPS endpoint or an explicitly designed private-network transport.

## Later verification
1. `docker compose ... config` and `docker compose ... ps` for the selected overlays.
2. `docker compose ... logs --tail=200 backend worker agent rag evaluation redis`.
3. Check DB migrations and auth/tenant isolation.
4. Run integration and agent smoke profiles, then frontend tests and backend tests.
5. Verify Redis cache hit/miss and 429/503 quota behavior.
6. Verify no secrets or raw prompt/document contents appear in logs and telemetry.
7. Inspect CI and image builds before claiming production readiness.

## Known limits
Demo JWT and local database credentials are **not** production authentication or secret management. RAG remains single-tenant per deployment; document-level ACL needs further work. Agent guardrails are heuristic, cache is planner-only, telemetry is in-memory, and fine-tuning requires optional ML dependencies. No AWS resources are deployed and end-to-end Compose has not been verified in this change series.
