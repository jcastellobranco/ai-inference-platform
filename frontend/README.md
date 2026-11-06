# AI Platform Console — React / TypeScript

A small, componentized developer UI for the inference service. **It is not a production authentication application.** Developers paste short-lived JWTs, held in memory only.

## Architecture

```text
src/
  main.tsx                  App shell and composition
  components/
    AccessTokenPanel.tsx    Development JWT input
    JobForm.tsx             Inference and RAG job submission
    JobsTable.tsx           Job status and citation display
  hooks/
    useJobs.ts              Fetch lifecycle, cancellation and loading state
  lib/
    api.ts                  Typed HTTP gateway and request errors
  types/
    jobs.ts                 Shared job models and RAG result parsing
  style.css                 Responsive theme, focus and status styles
```

UI components do not perform HTTP calls directly. The typed API layer handles endpoints and authorization headers, while `useJobs` owns fetching, cancellation and client state. The forms own temporary local input and have loading/disabled behavior. Changing the token clears jobs and cancels outstanding requests to avoid showing data from another tenant.

## Commands

```bash
npm install
npm run test
npm run build
npm run dev
```

Set `VITE_API_URL` to the inference backend gateway if it differs from `/api`. The existing Nginx Docker image proxies `/api`.

## Limitations and next work

The frontend currently displays the existing job API responses and submits RAG jobs, but it does not provide document management or an OAuth/OIDC login. Token claims are verified by the backend, not by the frontend; server-side PostgreSQL RLS remains the isolation authority. Job status is refreshed manually to avoid unnecessary polling. For a larger app, consider React Router, a query cache and component-level testing, but avoid unnecessary complexity until justified by actual workflows.
