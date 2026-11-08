# ATLAS + Multi-Agent + MCP: local integration

**Status:** Cross-repository code committed; end-to-end Compose has not been executed or verified yet. This is an experimental **single-tenant local demo**, not a production service.

## Architecture

```text
JWT browser/client -> ATLAS FastAPI POST /v1/agent/jobs
                    -> PostgreSQL RLS jobs queue
                    -> ATLAS worker (lease/fencing/retries)
                    -> private HTTP POST agent:8000/internal/v1/execute
                    -> Multi-Agent planner (offline deterministic)
                    -> DAG executor -> MCP stdio -> scoped word_count
                    -> worker persists JSON result
                    -> GET /v1/jobs/{id} (tenant-bound)
```

The ATLAS worker uses the same queue and JWT tenant isolation as existing jobs. The private agent API uses a service key and checks the configured tenant. The MCP server separately enforces configured process-level scopes. The frontend does not call the internal agent service directly.

## First-time setup

Clone these five sibling repositories in one directory: `ai-inference-platform`, `rag-document-intelligence`, `llm-evaluation-observability`, `multi-agent-orchestration`, and `mcp-tool-platform`.

```bash
cd ai-inference-platform
cp .env.example .env
# Populate all existing required secrets in .env (see README).
# Add a unique random secret with at least 32 characters:
# ATLAS_AGENT_SERVICE_KEY=<random-secret>
```

Launch the existing fullstack + RAG/evaluation + new agent overlay:

```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml -f docker-compose.agents.yml up -d --build
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml -f docker-compose.agents.yml ps
```

Run the **agent-specific** smoke:

```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml -f docker-compose.agents.yml --profile smoke run --rm agent-smoke
```

Expected on success: `SUCCESS: ATLAS JWT -> PostgreSQL queue -> worker -> Multi-Agent -> MCP stdio`.

Run existing RAG/evaluation smoke separately:

```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml -f docker-compose.agents.yml --profile smoke run --rm integration-smoke
```

If an agent job fails, inspect `docker compose ... logs worker agent backend`. Agent execution currently defaults to offline planning, which counts the words in the supplied question via a **real MCP stdio tool invocation**. This is not yet a document-grounded multi-agent task or a frontend agent workflow.

## Security and limits

- This example is single-tenant, pinned to UUID `11111111-1111-4111-8111-111111111111`.
- Never expose the agent container port publicly. `ATLAS_AGENT_SERVICE_KEY` must be distinct from JWT, RAG and evaluation secrets.
- The agent subprocess inherits a narrow tool scope allowlist; it does not accept caller-selected scopes.
- No public authentication exists on the Multi-Agent demo endpoints; only the internal endpoint uses a service key. Keep the service private.
- Worker job timeout and lease currently bound the overall agent execution; no lease renewal, distributed cancellation, or durable checkpoints inside Multi-Agent.
- Real model planning is implemented separately but the ATLAS worker intentionally uses `offline` until the integrated path is verified.
- The current Docker integration mounts the MCP source read-only and starts the MCP server through the SDK installed in the Multi-Agent image.
- Do not claim successful execution until the smoke tests have actually run.

## Next steps

Add an authenticated React UI for agent job submission and status; integrate RAG evidence into the agent workflow; use a hybrid replan strategy; add cross-service tracing and benchmarks.
