"""Exercise the real browser auth flow against migrated PostgreSQL."""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app import browser_auth

@pytest.fixture
def auth_db(monkeypatch):
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to the migrated runtime-role DSN")
    engine = create_engine(url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(browser_auth, "SessionLocal", session_factory)
    email = "atlas-auth-" + uuid4().hex + "@example.com"
    monkeypatch.setenv("ATLAS_BOOTSTRAP_EMAIL", email)
    # The bootstrap flow requires an empty user table; run only when empty.
    with session_factory() as db:
        if db.execute(text("SELECT EXISTS(SELECT 1 FROM app_users)")).scalar():
            pytest.skip("Auth integration requires an empty bootstrap database")
    yield email
    owner_url = os.getenv("TEST_OWNER_DATABASE_URL")
    if owner_url:
        owner_engine = create_engine(owner_url)
        with owner_engine.begin() as db:
            db.execute(text("DELETE FROM browser_sessions WHERE user_id IN (SELECT id FROM app_users WHERE email=:email)"), {"email": email})
            db.execute(text("DELETE FROM app_users WHERE email=:email"), {"email": email})
        owner_engine.dispose()
    engine.dispose()

def test_bootstrap_session_csrf_and_logout(auth_db):
    email = auth_db
    client = TestClient(app, base_url="http://localhost:8080")
    assert client.get("/auth/setup").json()["registration_available"] is True
    credentials = {"email": email, "password": "unique-test-password-with-20-chars"}
    headers = {"Origin": "http://localhost:8080"}
    registered = client.post("/auth/register", json=credentials, headers=headers)
    assert registered.status_code == 201, registered.text
    assert "atlas_session" in client.cookies
    assert client.get("/auth/setup").json()["registration_available"] is False
    assert client.get("/auth/me").status_code == 200
    assert client.get("/v1/jobs").status_code == 200
    assert client.post("/v1/jobs", json={"prompt": "hello"}).status_code == 403
    csrf = client.cookies["atlas_csrf"]
    created = client.post("/v1/jobs", json={"prompt": "hello"},
                          headers={**headers, "X-CSRF-Token": csrf})
    assert created.status_code == 201, created.text
    assert client.post("/auth/logout", headers={**headers, "X-CSRF-Token": csrf}).status_code == 204
    assert client.get("/auth/me").status_code == 401
    assert client.post("/auth/login", json=credentials, headers={"Origin": "http://evil.example"}).status_code == 403
    assert client.post("/auth/login", json=credentials, headers=headers).status_code == 200

def test_bootstrap_email_mismatch_and_setup(auth_db):
    client = TestClient(app, base_url="http://localhost:8080")
    status = client.get("/auth/setup").json()
    assert status == {"registration_available": True, "account_exists": False, "bootstrap_configured": True}
    result = client.post("/auth/register", json={
        "email": "other@example.com", "password": "strong-test-password-12345",
    }, headers={"Origin": "http://localhost:8080"})
    assert result.status_code == 403
    assert result.json()["detail"] == "Email does not match the configured bootstrap email"
