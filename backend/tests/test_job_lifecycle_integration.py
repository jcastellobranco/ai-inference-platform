"""Real PostgreSQL lifecycle tests using tenant and dedicated worker roles."""
import os
from uuid import UUID
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app import worker

TENANT_A = "11111111-1111-4111-8111-111111111111"
TENANT_B = "22222222-2222-4222-8222-222222222222"

@pytest.fixture
def sessions():
    runtime_url = os.getenv("TEST_DATABASE_URL")
    worker_url = os.getenv("WORKER_TEST_DATABASE_URL")
    if not runtime_url or not worker_url:
        pytest.skip("Requires TEST_DATABASE_URL and WORKER_TEST_DATABASE_URL")
    runtime_engine = create_engine(runtime_url)
    worker_engine = create_engine(worker_url)
    try:
        yield sessionmaker(bind=runtime_engine), sessionmaker(bind=worker_engine)
    finally:
        runtime_engine.dispose()
        worker_engine.dispose()

def create_job(runtime, tenant, prompt):
    with runtime.begin() as session:
        session.execute(text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant":tenant})
        return session.execute(text("""
          INSERT INTO jobs(tenant_id,prompt,status,created_by)
          VALUES (:tenant,:prompt,'queued','integration-test') RETURNING id
        """), {"tenant":tenant,"prompt":prompt}).scalar_one()

def read_job(runtime, tenant, job_id):
    with runtime.begin() as session:
        session.execute(text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant":tenant})
        return session.execute(text("""
          SELECT status,result,error,attempts,leased_until,finished_at
          FROM jobs WHERE id=:id
        """), {"id":job_id}).mappings().first()

def delete_job(runtime, tenant, job_id):
    with runtime.begin() as session:
        session.execute(text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant":tenant})
        session.execute(text("DELETE FROM jobs WHERE id=:id"), {"id":job_id})

def test_claim_finish_and_isolation(sessions):
    runtime, service = sessions
    # Inserting one test job avoids depending on any background worker process.
    job_id = create_job(runtime, TENANT_A, "test unique job")
    try:
        assert read_job(runtime, TENANT_B, job_id) is None
        claimed = worker.claim_job(service)
        assert claimed is not None
        assert claimed["id"] == job_id
        assert str(claimed["tenant_id"]) == TENANT_A
        assert claimed["attempts"] == 1
        assert worker.finish_job(service, claimed, result="TEST UNIQUE JOB")
        own = read_job(runtime, TENANT_A, job_id)
        assert own["status"] == "completed"
        assert own["result"] == "TEST UNIQUE JOB"
        assert own["attempts"] == 1
        assert own["finished_at"] is not None
        assert not worker.finish_job(service, claimed, result="overwritten")
        assert read_job(runtime, TENANT_B, job_id) is None
    finally:
        delete_job(runtime, TENANT_A, job_id)

def test_retry_fencing_and_exhaustion(sessions, monkeypatch):
    runtime, service = sessions
    monkeypatch.setattr(worker, "MAX_ATTEMPTS", 2)
    job_id = create_job(runtime, TENANT_A, "failing task")
    try:
        first = worker.claim_job(service)
        assert first is not None and first["id"] == job_id
        assert worker.finish_job(service, first, error="TemporaryFailure")
        retrying = read_job(runtime, TENANT_A, job_id)
        assert retrying["status"] == "retrying"
        assert retrying["leased_until"] is not None
        assert retrying["finished_at"] is None
        assert worker.claim_job(service) is None
        # Test clock advancement by moving the persisted retry due time.
        with service.begin() as db:
            db.execute(text("UPDATE jobs SET leased_until=now()-interval '1 second' WHERE id=:id"), {"id":job_id})
        second = worker.claim_job(service)
        assert second is not None and second["id"] == job_id
        assert second["attempts"] == 2
        assert second["lease_token"] != first["lease_token"]
        assert not worker.finish_job(service, first, result="stale worker")
        assert worker.finish_job(service, second, error="PermanentFailure")
        done = read_job(runtime, TENANT_A, job_id)
        assert done["status"] == "failed"
        assert done["error"] == "PermanentFailure"
        assert done["leased_until"] is None
        assert done["finished_at"] is not None
    finally:
        delete_job(runtime, TENANT_A, job_id)
