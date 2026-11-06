"""Real PostgreSQL / JWT test for the RAG job type and per-tenant RLS."""
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
    token = jwt.encode({"sub":"rag-test","tenant_id":tenant,"iss":main.ISSUER,
                        "aud":main.AUDIENCE,"exp":datetime.now(timezone.utc)+timedelta(minutes=5)},
                       secret,algorithm="HS256")
    return {"Authorization":f"Bearer {token}"}

def test_rag_submit_claim_and_isolation(monkeypatch):
    runtime_url=os.getenv("TEST_DATABASE_URL")
    worker_url=os.getenv("WORKER_TEST_DATABASE_URL")
    if not runtime_url or not worker_url:
        pytest.skip("Real runtime and worker DB roles required")
    runtime_engine=create_engine(runtime_url)
    worker_engine=create_engine(worker_url)
    runtime=sessionmaker(bind=runtime_engine,expire_on_commit=False)
    service=sessionmaker(bind=worker_engine,expire_on_commit=False)
    monkeypatch.setattr(db,"SessionLocal",runtime)
    monkeypatch.setenv("RAG_SERVICE_TENANT_ID",A)
    monkeypatch.setenv("RAG_SERVICE_URL","https://rag.example.test")
    monkeypatch.setenv("RAG_SERVICE_API_KEY","test-key")
    secret="test-secret-"+uuid4().hex
    monkeypatch.setattr(main,"SECRET",secret)
    client=TestClient(main.app)
    job_id=None
    try:
        deny=client.post("/v1/rag/jobs",headers=auth(secret,B),json={"question":"Can I see tenant A?"})
        assert deny.status_code == 403
        created=client.post("/v1/rag/jobs",headers=auth(secret,A),
                            json={"question":"Kubernetes pods"})
        assert created.status_code == 201, created.text
        job_id=created.json()["id"]
        assert created.json()["job_type"] == "rag"
        assert client.get(f"/v1/jobs/{job_id}",headers=auth(secret,B)).status_code == 404
        claimed=worker.claim_job(service)
        assert claimed is not None and str(claimed["id"]) == str(job_id)
        assert claimed["job_type"] == "rag"
        assert claimed["reference_answer"] is None
        assert worker.finish_job(service,claimed,result='{"mode":"insufficient_evidence"}')
        detail=client.get(f"/v1/jobs/{job_id}",headers=auth(secret,A))
        assert detail.status_code == 200
        assert detail.json()["status"] == "completed"
        assert client.get(f"/v1/jobs/{job_id}",headers=auth(secret,B)).status_code == 404
    finally:
        if job_id:
            with runtime.begin() as session:
                session.execute(text("SELECT set_config('app.tenant_id', :t, true)"),{"t":A})
                session.execute(text("DELETE FROM jobs WHERE id=:id"),{"id":job_id})
        runtime_engine.dispose()
        worker_engine.dispose()
