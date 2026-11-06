# Durable job processing design

The backend stores job requests in PostgreSQL. A separate worker process claims jobs using an atomic UPDATE with SELECT FOR UPDATE SKIP LOCKED, avoiding duplicate claims between concurrent workers. Each claim increments the attempt counter and sets a lease deadline.

## Limitations to address before deployment

The current worker is an **integration scaffold** and not production-ready. The service role must be provisioned with appropriate RLS policy or dedicated narrowly scoped privileges; the API runtime role cannot bypass RLS. Crash recovery currently reclaims expired leases but does not implement periodic lease renewal. There is no idempotency guarantee for side effects, no dead-letter table, and the worker uses a deterministic uppercase demonstration provider instead of an LLM. Jobs with exhausted retries require a terminal-state sweeper.

## Next milestones

- Create worker-specific DB role, restricted policies and migration
- Add lease heartbeat and fencing token to prevent stale workers committing
- Separate retryable failures from permanent failures
- Integrate real inference providers and metrics
- Validate worker concurrency with PostgreSQL integration tests
