"""PostgreSQL-backed job leasing with SKIP LOCKED and crash recovery."""
import asyncio
import os
import signal
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from .db import SessionLocal

POLL_SECONDS = float(os.getenv("WORKER_POLL_SECONDS", "1"))
LEASE_SECONDS = int(os.getenv("WORKER_LEASE_SECONDS", "120"))
MAX_ATTEMPTS = int(os.getenv("WORKER_MAX_ATTEMPTS", "3"))
WORKER_ID = os.getenv("WORKER_ID", "worker-local")

def claim_job():
    """Atomic claim, scoped by DB permissions; worker uses privileged service role."""
    with SessionLocal.begin() as db:
        row = db.execute(text("""
            WITH next_job AS (
              SELECT id FROM jobs
              WHERE (status = 'queued' OR (status = 'running' AND leased_until < now()))
                AND attempts < :max_attempts
              ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1
            )
            UPDATE jobs j SET status='running', attempts=j.attempts+1,
              leased_until=now() + (:lease * interval '1 second'), worker_id=:worker
            FROM next_job WHERE j.id=next_job.id
            RETURNING j.id, j.tenant_id, j.prompt, j.attempts
        """), {"max_attempts": MAX_ATTEMPTS, "lease": LEASE_SECONDS, "worker": WORKER_ID}).mappings().first()
        return dict(row) if row else None

def finish_job(job_id, tenant_id, result=None, error=None):
    with SessionLocal.begin() as db:
        db.execute(text("""
            UPDATE jobs SET status=:status, result=:result, error=:error,
              leased_until=NULL, finished_at=now()
            WHERE id=:id AND tenant_id=:tenant AND worker_id=:worker AND status='running'
        """), {"status": "completed" if error is None else "failed", "result": result,
               "error": error, "id": job_id, "tenant": tenant_id, "worker": WORKER_ID})

async def infer(prompt: str) -> str:
    """Deterministic placeholder; replace with an authenticated model provider."""
    await asyncio.sleep(0)
    return prompt.upper()

async def run_forever():
    while True:
        item = await asyncio.to_thread(claim_job)
        if not item:
            await asyncio.sleep(POLL_SECONDS)
            continue
        try:
            output = await asyncio.wait_for(infer(item["prompt"]), timeout=LEASE_SECONDS - 5)
            await asyncio.to_thread(finish_job, item["id"], item["tenant_id"], result=output)
        except Exception as exc:
            await asyncio.to_thread(finish_job, item["id"], item["tenant_id"], error=type(exc).__name__)

if __name__ == "__main__":
    asyncio.run(run_forever())
