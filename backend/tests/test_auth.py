from datetime import datetime, timedelta, timezone
from uuid import uuid4
import jwt
from fastapi.testclient import TestClient
from app.main import app

def test_liveness():
    assert TestClient(app).get("/health/live").json() == {"status": "ok"}

def test_invalid_issuer_rejected(monkeypatch):
    monkeypatch.setattr("app.main.SECRET", "a" * 40)
    claims = {"sub": "tester", "tenant_id": str(uuid4()), "iss": "wrong",
              "aud": "ai-platform", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    token = jwt.encode(claims, "a" * 40, algorithm="HS256")
    response = TestClient(app).get("/v1/jobs", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
