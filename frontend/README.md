# ATLAS · AI Platform Console

A responsive React / TypeScript workspace for the inference, knowledge, and evaluation services.

## Screens

- **Overview**: recent activity, tenant-scoped documents and job counts, and suggested workflows.
- **Knowledge base**: PDF uploads (10 MiB, 100 pages), text ingestion, persistent source catalogue, deletion.
- **RAG playground**: hybrid lexical/vector search, source excerpts, citations, RAG execution and optional evaluation.
- **Job runs**: inference submission, job status filters, answers and evaluation results.

## Structure

```text
src/
  main.tsx                 app composition and session-scoped refresh
  pages/
    OverviewPage.tsx       overview metrics and activity
    DocumentsPage.tsx      document ingestion and catalogue
    PlaygroundPage.tsx     retrieval and RAG queries
    JobsPage.tsx           durable queue activity
  components/
    AppShell.tsx           global navigation
    AccessDialog.tsx       ephemeral JWT entry
    EmptyState.tsx         reusable empty states
    StatCard.tsx           KPI cards
    StatusBadge.tsx        job state indicator
    SectionHeader.tsx     reusable headings
  hooks/
    useJobs.ts             fetch state and cancellation
    useKnowledge.ts        catalogue state and mutations
  lib/
    api.ts                 authenticated inference gateway
    knowledgeApi.ts        authenticated knowledge gateway
  types/
    jobs.ts                job / result contracts
    knowledge.ts           document / retrieval contracts
  style.css                responsive design system
```

The browser only calls the inference backend. FastAPI's `/v1/knowledge/*` BFF validates JWT tenant identity and uses the server-side RAG service key; the client never knows the private key. Tenant-scoped PostgreSQL RLS remains the authorization boundary.

## Run integrated on Mac

Keep all three repositories checked out side-by-side. In `ai-inference-platform`:

```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml up --build -d
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml --profile smoke run --rm integration-smoke
```

Open http://localhost:8080. Use **Manage access** to paste the short-lived development JWT. Upload text or PDF in **Knowledge base**, retrieve sources in **RAG playground**, optionally run the durable RAG job, then inspect **Job runs**.

Run frontend checks separately:

```bash
cd frontend
npm install
npm run test
npm run build
```

The Vite development server requires a configured proxy or a browser-accessible API URL; the integrated Nginx setup already proxies `/api` to the backend.

## Limitations

This is a development interface, not an OAuth/OIDC login. The JWT is kept in page memory only. Retrieval mode returns evidence, not a synthesized answer; the RAG job defaults to extractive first-chunk mode unless generation is explicitly enabled. Evaluation metrics are lexical comparisons, not proof of factuality. Lists show the latest 100 jobs/documents. Active jobs are refreshed on a four-second interval until terminal state.
