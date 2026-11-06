import asyncio
from fastapi.testclient import TestClient
from inference_platform.api import create_app

def test_job_lifecycle_and_auth():
    app = create_app(key="test-secret", workers=1)
    with TestClient(app) as client:
        assert client.post("/v1/jobs", json={"prompt": "hello"}).status_code == 401
        headers = {"x-api-key": "test-secret"}
        created = client.post("/v1/jobs", headers=headers, json={"prompt": "hello"})
        assert created.status_code == 202
        job_id = created.json()["id"]
        for _ in range(50):
            status = client.get(f"/v1/jobs/{job_id}", headers=headers).json()
            if status["status"] == "completed":
                break
            import time
            time.sleep(0.01)
        assert status["result"] == "HELLO"
        assert client.get("/v1/metrics", headers=headers).json()["jobs"]["completed"] == 1
        assert client.get("/v1/jobs/missing", headers=headers).status_code == 404

def test_requires_key():
    import pytest
    with pytest.raises(RuntimeError):
        create_app(key="")
