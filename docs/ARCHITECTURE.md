# Inference platform architecture

## Current reference implementation

FastAPI accepts authenticated requests, validates input size, and places jobs in a bounded `asyncio.Queue`. A fixed worker pool invokes a pluggable asynchronous provider, with per-attempt timeout, bounded retries and exponential backoff. The API exposes job state, readiness and simple JSON metrics.

## Operational constraints

- **Single-process only.** Queue and job records live in memory; multiple Uvicorn workers will not share them.
- Jobs are lost on restart. The service is not durable and does not offer exactly-once processing.
- Shutdown waits for queued jobs; a stalled provider can delay shutdown.
- A single shared API key is suitable only for controlled demonstrations, not tenant isolation.
- Job result storage is unbounded; add TTL retention and quotas before any long-running deployment.
- The default provider is deterministic uppercase transformation, **not a language model**.

## Production evolution

Replace in-memory queue with SQS or Redis Streams, store jobs in PostgreSQL, use worker services with horizontal autoscaling, authenticate via OIDC/JWT, instrument OpenTelemetry traces and Prometheus metrics, add idempotency keys and dead-letter handling. Keep queue visibility timeout longer than inference timeout and implement lease renewal for long jobs.

## Local execution

```bash
pip install -e '.[dev]'
export INFERENCE_API_KEY=local-demo-secret
uvicorn inference_platform.api:create_app --factory --reload
curl -X POST http://127.0.0.1:8000/v1/jobs -H 'x-api-key: local-demo-secret' -H 'content-type: application/json' -d '{"prompt":"hello"}'
pytest -q
```
