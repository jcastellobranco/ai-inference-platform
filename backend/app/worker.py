"""Durable PostgreSQL worker with leased claims and fencing tokens.

Requires WORKER_DATABASE_URL for a dedicated service account with an explicit
RLS policy. Never connect with the tenant-facing API database account.
"""
import asyncio
import os
from uuid import uuid4
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

POLL_SECONDS = float(os.getenv("WORKER_POLL_SECONDS", "1"))
LEASE_SECONDS = int(os.getenv("WORKER_LEASE_SECONDS", "120"))
MAX_ATTEMPTS = int(os.getenv("WORKER_MAX_ATTEMPTS", "3"))
WORKER_ID = os.getenv("WORKER_ID") or str(uuid4())

def make_session():
    url = os.environ.get("WORKER_DATABASE_URL")
    if not url:
        raise RuntimeError("WORKER_DATABASE_URL is required (dedicated worker DB role)")
    return sessionmaker(bind=create_engine(url, pool_pre_ping=True, pool_size=2), expire_on_commit=False)

def claim_job(sessions):
    """Lock one job and atomically acquire a unique fencing token."""
    lease_token = str(uuid4())
    with sessions.begin() as db:
        row = db.execute(text("""
            WITH candidate AS (
                SELECT id FROM jobs
                WHERE (status = 'queued' OR (status = 'running' AND leased_until < now()) OR (status = 'retrying' AND leased_until <= now()))
                  AND attempts < :max_attempts
                ORDER BY created_at, id
                FOR UPDATE SKIP LOCKED LIMIT 1
            )
            UPDATE jobs AS j SET status='running', attempts=j.attempts+1,
                leased_until=now() + (:lease * interval '1 second'),
                worker_id=:worker, lease_token=:token
            FROM candidate WHERE j.id=candidate.id
            RETURNING j.id, j.tenant_id, j.prompt, j.attempts, j.lease_token, j.job_type, j.reference_answer, j.agent_workflow
        """), {"max_attempts": MAX_ATTEMPTS, "lease": LEASE_SECONDS,
               "worker": WORKER_ID, "token": lease_token}).mappings().first()
        return dict(row) if row else None

def finish_job(sessions, job, *, result=None, error=None, permanent=False):
    """Fencing token prevents a timed-out former worker from overwriting a new lease."""
    with sessions.begin() as db:
        status = "completed" if error is None else ("failed" if permanent or job["attempts"] >= MAX_ATTEMPTS else "retrying")
        # Retry time is persisted: retries must not become stranded with a NULL lease.
        retry_delay = min(60, 2 ** min(job["attempts"] - 1, 6))
        updated = db.execute(text("""
            UPDATE jobs SET status=:status, result=:result, error=:error,
                leased_until=CASE WHEN :status='retrying'
                    THEN now() + (:retry_delay * interval '1 second') ELSE NULL END,
                finished_at=CASE WHEN :status='retrying' THEN NULL ELSE now() END,
                lease_token=NULL, worker_id=NULL
            WHERE id=:id AND tenant_id=:tenant AND worker_id=:worker
              AND lease_token=:token AND status='running' AND leased_until > now()
        """), {"status": status, "result": result, "error": error,
               "retry_delay": retry_delay, "id": job["id"],
               "tenant": job["tenant_id"], "worker": WORKER_ID,
               "token": job["lease_token"]}).rowcount
        return updated == 1

def expire_exhausted(sessions):
    """Move exhausted expired leases to terminal state."""
    with sessions.begin() as db:
        return db.execute(text("""
            UPDATE jobs SET status='failed', error='retry budget exhausted',
                leased_until=NULL, finished_at=now()
            WHERE status='running' AND leased_until < now()
              AND attempts >= :max_attempts
        """), {"max_attempts": MAX_ATTEMPTS}).rowcount

async def infer(prompt: str) -> str:
    """Demonstration provider only, not a real language model."""
    await asyncio.sleep(0)
    return prompt.upper()

async def run_forever():
    if LEASE_SECONDS < 10 or MAX_ATTEMPTS < 1 or POLL_SECONDS <= 0:
        raise ValueError("Invalid worker lease/retry/poll configuration")
    sessions = make_session()
    while True:
        await asyncio.to_thread(expire_exhausted, sessions)
        job = await asyncio.to_thread(claim_job, sessions)
        if job is None:
            await asyncio.sleep(POLL_SECONDS)
            continue
        try:
            if job["job_type"] == "rag":
                from .rag_jobs import execute_rag
                operation = execute_rag(job)
            elif job["job_type"] == "agent":
                from .agent_jobs import execute_agent
                operation = execute_agent(job)
            else:
                operation = infer(job["prompt"])
            output = await asyncio.wait_for(operation, timeout=LEASE_SECONDS - 5)
            await asyncio.to_thread(finish_job, sessions, job, result=output)
        except Exception as exc:
            from .generation import GroundingError
            await asyncio.to_thread(finish_job, sessions, job,
                                    error=type(exc).__name__,
                                    permanent=isinstance(exc, GroundingError))

if __name__ == "__main__":
    asyncio.run(run_forever())
