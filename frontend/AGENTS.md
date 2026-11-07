# Frontend agent instructions

Inherits repository root AGENTS.md.

- React 19, TypeScript and Vite. Follow existing components and styling before adding dependencies.
- Keep API calls in client modules; do not embed private service credentials or direct private-service URLs in the browser.
- Maintain loading, empty, error, retrying and completed states; never show a job as complete before the API confirms it.
- Handle token changes by clearing tenant-sensitive local UI state; avoid displaying stale results from previous sessions.
- Prefer typed API contracts and accessible controls with labels and disabled/loading states.
- Preserve backward compatibility for previously persisted job results that lack newer optional fields.
- Validate with `npm test` and `npm run build` when available; report if not run.
