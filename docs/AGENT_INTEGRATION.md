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

## Document-grounded research workflow (experimental)

The ATLAS Multi-Agent React page now offers two execution modes: **MCP tools** and **Research (LangGraph + RAG + MCP)**. The authenticated ATLAS API accepts `{"question":"...","workflow":"research"}` at `POST /v1/agent/jobs`. The database migration `009_agent_workflow.sql` stores the choice, and the existing worker forwards it to the private agent API.

Research mode invokes the existing four-stage LangGraph (planner/researcher/analyst/reviewer), retrieving evidence from the tenant-bound RAG vector service; then it invokes the existing scoped MCP tool. Its result includes `research.findings`, `research.trace`, and MCP `trace`. A lack of retrieved evidence is recorded as `insufficient_evidence`, not a fabricated answer. No model synthesis or RAG-to-MCP argument chaining is implemented yet.

For research mode the `agent` container requires `ATLAS_RAG_URL`, `ATLAS_RAG_API_KEY`, `ATLAS_TENANT_ID`, provided by `docker-compose.agents.yml` when layered with `docker-compose.integrated.yml`. Do not publish the agent service port. The ATLAS frontend never receives RAG or MCP credentials.

**Not yet validated in Docker:** run the backend, frontend, Multi-Agent and RAG test suites, then submit a research job after ingesting documents. The existing `agent-smoke` tests only the default tools workflow; it does not exercise research mode.

## Optional grounded Research answer (new)

Research now supports a cited natural-language answer after retrieval, using the existing ATLAS generation adapter in the **worker**. It is disabled by default and never sends provider credentials to the browser or agent container.

Configure the root `.env` (do not commit secrets):

```dotenv
RAG_GENERATION_ENABLED=true
GENERATION_API_URL=https://api.openai.com/v1
GENERATION_API_KEY=<your-provider-key>
GENERATION_MODEL=<your-supported-chat-model>
GENERATION_MAX_OUTPUT_TOKENS=500
```

The existing adapter currently requires the OpenAI HTTPS endpoint shown above. Recreate the worker after changing these values:

```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml -f docker-compose.agents.yml up -d --build --force-recreate worker frontend
```

Submit a **new** Research run. Old persisted results remain unchanged. The UI displays the grounded answer with numbered source citations, and puts retrieved chunks in a collapsible evidence section. When generation is disabled it clearly says that no answer was generated and exposes the evidence. If evidence is insufficient, no answer is fabricated. Generation failures remain subject to existing worker retry behavior.

Run the focused backend test: `pytest backend/tests/test_agent_generation.py` in an environment with backend dependencies installed. This change has not been validated by executing the Docker test suite.

## Compliance Auditor MVP — supplier baseline v1

**Business goal:** screen indexed supplier agreements for evidence of four baseline clauses: confidentiality, security incident notification, personal-data protection, and termination. This is a deterministic, human-in-the-loop **evidence checklist**, not a legal audit or compliance verdict.

In the Multi-Agent page choose **Compliance Auditor · Supplier baseline** and submit a task. The authenticated `POST /v1/agent/jobs` accepts `{"question":"...","workflow":"compliance"}`. The job is persisted in the existing PostgreSQL queue; the worker calls the existing tenant-scoped LangGraph/RAG research path and evaluates up to five returned chunks against versioned checklist terms. The UI displays evidence candidates, missing-from-retrieval flags and source/chunk identifiers. Every check requires human review. No match is **not** proof of noncompliance; a match is **not** proof of compliance. Do not use this as an automated legal decision.

The workflow uses the existing Research RAG adapter, so document ingestion and retrieval must be configured and the indexed corpus must contain relevant supplier documents. No model key is required for this conservative baseline. The underlying research MCP word-count step is retained for backwards compatibility, but is not the business outcome.

After pulling, apply migration `010_compliance_workflow.sql` using the existing migration service and rebuild backend, worker and frontend:
```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml -f docker-compose.agents.yml up -d --build --force-recreate migrate backend worker frontend
```
Run `pytest backend/tests/test_compliance_audit.py` with backend dependencies installed. Docker integration, migrations and frontend build have **not** been executed by this change.

**Limitations and next release:** the checklist is fixed, lexical and excerpt-scoped; no cross-document clause comparison, exhaustive coverage, calibrated relevance threshold, configurable policy upload, verified severity, workflow approvals, or downloadable compliance report yet. The next iteration should separate authoritative policy requirements from contracts, add structured extraction and document coverage, and produce reviewer-confirmed findings.

## Product-first document-scoped compliance review (v1.1)

The **Compliance Auditor** page now provides a business-oriented path:

1. Upload a reference policy and contracts in **Knowledge Base**.
2. Select exactly **one reference policy** and **1–4 contracts**.
3. Click **Analisar contratos**. Additional instructions are optional and are *not used as dynamic audit rules* in this release.
4. Review a **separate report for each selected contract**, with concise messages and expandable excerpts from both policy and contract. Technical execution metrics remain behind a disclosure control.

Selection is **enforced in the backend**, not only in the browser:

- `POST /v1/agent/jobs` with `{"workflow":"compliance","question":"...","policy_document_id":"<uuid>","target_document_ids":["<uuid>"]}` persists document UUIDs in new nullable columns on `jobs` (migration `011_compliance_documents.sql`).
- The durable worker reads **only** those UUIDs from the private RAG service `GET /v1/documents/{document_id}/content`. This endpoint is API-key-authenticated, tenant-restricted and reads each document using a tenant-scoped SQL query with RLS. A missing/unavailable document fails closed; the worker never falls back to searching the whole Knowledge Base.
- For every one of four fixed checklist items, the worker looks for related evidence independently in the selected policy and each selected contract. An absence is labeled a **potential gap for human review**, not proof of noncompliance. A textual hit does not prove contractual sufficiency. Potential negative clauses are flagged for attention using a conservative heuristic.
- Old unscoped compliance jobs remain readable as legacy results, but the new UI requires a selection for new compliance requests. Research and diagnostic agent modes remain available under advanced options.

**Business limitations:** This is a deterministic, bounded screening against all indexed chunks of selected documents, not an LLM legal interpretation. It cannot yet extract arbitrary rules from a reference policy, establish the legal meaning of clauses, or issue final compliance approval. Historical reports cannot be upgraded automatically, and contract analysis is limited to four targets per run.

**Platform engineering evidence:** The product demonstrates authenticated BFF access, private RAG service APIs, tenant RLS, durable PostgreSQL jobs, worker leases/fencing, per-contract provenance, bounded retrieval, traceability and backward-compatible result schemas.

### Running the updated integrated stack

Both sibling repositories are required: `ai-inference-platform` and `rag-document-intelligence`. Pull changes in **both** (the RAG service has a new document-content endpoint):

```bash
(cd ../rag-document-intelligence && git pull --ff-only)
git pull --ff-only
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml -f docker-compose.agents.yml up -d --build --force-recreate migrate rag backend worker frontend
```

When `rag` is recreated, the related migration service must be healthy/completed. **Do not run `down -v`**; data volumes should be preserved.

Checks:
- `pytest backend/tests/test_compliance_documents.py backend/tests/test_compliance_api.py`
- In the RAG repository: `pytest tests/test_document_scope.py`
- In `frontend/`: `npm run check`
- Smoke: load policy + three sample contracts and verify separate report cards and policy/contract excerpt provenance; delete one selected document after submission to verify closed failure (not mixed evidence).

These checks are not a substitute for a live integrated smoke test with indexed PDFs.
