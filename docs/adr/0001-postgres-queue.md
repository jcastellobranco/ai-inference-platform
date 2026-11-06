# ADR-0001: PostgreSQL-backed task queue for the portfolio reference platform

**Status:** Accepted for local reference implementation; revisit before production.

## Context

The system needs durable inference jobs with tenant isolation, bounded worker concurrency, retries, and recovery from process crashes. A separate Redis/SQS broker would add another deployment dependency to the local demonstration.

## Decision

Store jobs in PostgreSQL, use `SELECT ... FOR UPDATE SKIP LOCKED` to claim work atomically, and process jobs in a separate worker container. API access uses a tenant-constrained role with PostgreSQL FORCE RLS. Workers use a separate service role with explicitly broader cross-tenant policies; its credentials never reach the browser.

Each claim generates a unique lease token. A worker may only complete a job if it still owns the active lease and token. Failed attempts enter a delayed `retrying` state with bounded exponential backoff. Attempts are capped.

## Consequences

**Benefits:** one durable datastore, transactional claims, no duplicate concurrent claim of the same row, simple local Compose architecture, auditable RLS behavior.

**Costs:** database polling, operational coupling of API and queue, additional write load, and contention at higher throughput. Fencing prevents stale writes but does not guarantee exactly-once external side effects. The current worker does not renew leases for long-running inference. `SKIP LOCKED` is not a fair scheduler, and there is no priority policy.

## When to migrate

Adopt SQS + Fargate workers or Redis Streams when throughput, independent scaling, dead-letter queues, or operational separation justify it. Keep the PostgreSQL job table as the system of record, and use an outbox to atomically publish work. Require idempotent handlers for at-least-once delivery.

## Verification requirements

- Two tenant identities: no cross-tenant reads or writes
- Two worker processes: each queued job claimed once per active lease
- Crash and expired lease: another worker reclaims safely
- Old lease token: stale completion rejected
- Retry budget exhausted: terminal failed state
- Container startup: migrations and runtime permissions verified
