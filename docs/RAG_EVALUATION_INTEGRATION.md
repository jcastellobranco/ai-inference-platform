# RAG → Inference → Evaluation integration

This integration is **an extractive retrieval demonstration**, not an LLM-based answer generator. The inference platform owns an authenticated, durable job queue and calls existing RAG and evaluation HTTP APIs. Retrieval returns bounded citations; the extractive answer copies the first returned chunk. When a reference answer is provided, the worker submits that output to the evaluation API and stores the returned metrics alongside citations. Without a reference, evaluation remains null.

## Security boundary

The current RAG HTTP service uses one tenant configured through `RAG_TENANT_ID`. To avoid cross-tenant disclosure, the inference API accepts RAG jobs **only** for `RAG_SERVICE_TENANT_ID`, which must be the same UUID configured as `RAG_TENANT_ID` on the RAG server. The worker checks the tenant again before making HTTP calls. Do **not** point multi-tenant jobs at an unpartitioned index or assume that an arbitrary tenant header authenticates identity.

Set these on both inference API and worker (service URLs must be reachable from the worker's container):

- `RAG_SERVICE_TENANT_ID`: allowed UUID, matching the RAG server's `RAG_TENANT_ID`
- `RAG_SERVICE_URL`: e.g. `http://rag:8000`
- `RAG_SERVICE_API_KEY`: matches the RAG server's `RAG_API_KEY`
- `EVAL_SERVICE_URL`: e.g. `http://eval:8000` (optional when no reference is supplied)
- `EVAL_SERVICE_API_KEY`: matches the evaluation server's `EVAL_API_KEY`

These credentials should be provisioned by secrets management outside local development. Production interservice communication should use a private network plus TLS or service mesh identity. Each service must restrict direct exposure to prevent bypass of the inference authorization layer.

## API

```http
POST /v1/rag/jobs
Authorization: Bearer <JWT>
Content-Type: application/json

{"question":"What is Kubernetes?","reference_answer":"Kubernetes orchestrates containers."}
```

The response is `201 {"id":"<uuid>","status":"queued","job_type":"rag"}`.
Poll `GET /v1/jobs/<uuid>` with the same JWT. The existing `result` column contains a **JSON string** with `mode`, `answer`, `citations`, and optional `evaluation`; this is a transitional contract and should be migrated to a JSONB result schema in a later version.

## Testing and limitations

The full-stack workflow applies migration 007, tests RLS on real PostgreSQL and checks HTTP contracts with mocked transports. It does not yet start the real RAG and Evaluation containers and perform a complete multi-container integration test. RAG's existing HTTP API currently uses SQLite FTS5; its separate pgvector hybrid pipeline is not yet wired into that HTTP API. Consequently **this integration does not yet query the pgvector index**. There is no true generative model or reference-free hallucination evaluator here.

Next steps: connect the pgvector-backed pipeline to the RAG HTTP API, add service-container integration tests, replace extracted chunk responses with a grounded generation provider, and run retrieval quality evaluations against a representative corpus.
