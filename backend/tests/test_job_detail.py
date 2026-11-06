from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import MagicMock, patch
import jwt
from fastapi.testclient import TestClient
from app.main import app

def test_job_detail_returns_404_without_disclosing_tenant(monkeypatch):
    secret = "x" * 40
    monkeypatch.setattr("app.main.SECRET", secret)
    token = jwt.encode({
        "sub": "tester", "tenant_id": str(uuid4()), "iss": "portfolio-dev",
        "aud": "ai-platform", "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }, secret, algorithm="HS256")
    session = MagicMock()
    session.execute.return_value.mappings.return_value.first.return_value = None
    from contextlib import contextmanager
    @contextmanager
    def fake_tenant_session(tenant):
        yield session
    with patch("app.main.tenant_session", fake_tenant_session):
        response = TestClient(app).get(f"/v1/jobs/{uuid4()}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404
