"""End-to-end API -> PostgreSQL -> worker -> API, with real RLS roles."""
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app import db, main, worker

A = "11111111-1111-4111-8111-111111111111"
B = "22222222-2222-4222-8222-222222222222"

def auth(secret, tenant):
    token = jwt.encode({
        "sub":"integration-user", "tenant_id":tenant, "iss":main.ISSUER,
        "aud":main.AUDIENCE, "exp":datetime.now(timezone.utc)+timedelta(minutes=5),
    }, secret, algorithm="HS256")
    return {"Authorization":f"Bearer {token}"}

def test_api_submit_worker_complete_and_tenant_404(monkeypatch):
    runtime_url = os.getenv("TEST_DATABASE_URL")
    worker_url = os.getenv("WORKER_TEST_DATABASE_URL")
    if not runtime_url or not worker_url:
        pytest.skip("PostgreSQL runtime and worker DSNs are required")
    runtime_engine = create_engine(runtime_url)
    worker_engine = create_engine(worker_url)
    runtime_sessions = sessionmaker(bind=runtime_engine, autoflush=False, expire_on_commit=False)
    worker_sessions = sessionmaker(bind=worker_engine)
    monkeypatch.setattr(db, "SessionLocal", runtime_sessions)
    secret = "integration-secret-" + uuid4().hex
    monkeypatch.setattr(main, "SECRET", secret)
    client = TestClient(main.app)
    job_id = None
    try:
        created = client.post("/v1/jobs", headers=auth(secret, A),
                              json={"prompt":"end to end inference"})
        assert created.status_code == 201, created.text
        job_id = created.json()["id"]
        assert created.json()["status"] == "queued"
        assert client.get(f"/v1/jobs/{job_id}", headers=auth(secret, B)).status_code == 404
        assert all(str(item["id"]) != str(job_id) for item in
                   client.get("/v1/jobs", headers=auth(secret, B)).json()["items"])
        claimed = worker.claim_job(worker_sessions)
        assert claimed is not None and str(claimed["id"]) == str(job_id)
        # Current provider is deliberately a deterministic demonstration implementation.
        assert worker.finish_job(worker_sessions, claimed, result=claimed["prompt"].upper())
        read = client.get(f"/v1/jobs/{job_id}", headers=auth(secret, A))
        assert read.status_code == 200, read.text
        assert read.json()["status"] == "completed"
        assert read.json()["result"] == "END TO END INFERENCE"
        assert read.json()["attempts"] == 1
        assert client.get(f"/v1/jobs/{job_id}", headers=auth(secret, B)).status_code == 404
    finally:
        if job_id is not None:
            with runtime_sessions.begin() as session:
                session.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t":A})
                session.execute(text("DELETE FROM jobs WHERE id=:id"), {"id":job_id})
        runtime_engine.dispose()
        worker_engine.dispose()
