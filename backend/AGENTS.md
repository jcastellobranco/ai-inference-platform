# Backend agent instructions

Inherits repository root AGENTS.md.

- Keep FastAPI route handlers thin; place business logic in service modules.
- Validate API inputs with Pydantic, enforce length/range bounds, and return safe errors.
- Tenant identity comes from the verified principal. Preserve RLS session context and least-privilege DB roles.
- The RAG service is tenant-bound per deployment; do not allow arbitrary client-selected upstream URLs or tenant IDs.
- Worker job claims must retain fencing tokens and lease checks; avoid duplicate side effects on retry.
- Provider calls need bounded timeouts; citation repair must remain bounded and evidence-grounded.
- Record stage timing and token usage without persisting secret keys or unnecessary raw source text.
- For changes to jobs, security or retrieval, add positive, negative and cross-tenant tests.
- Review `backend/migrations/` before editing schema. Never rewrite an applied migration; add a new migration.
