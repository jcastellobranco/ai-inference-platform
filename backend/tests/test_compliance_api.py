"""Public audit job validation and tenant binding."""
from contextlib import contextmanager
from uuid import uuid4

from fastapi.testclient import TestClient

from app import main

TENANT = "11111111-1111-4111-8111-111111111111"


def test_document_selection_validation_precedes_queue(monkeypatch):
    main.app.dependency_overrides[main.principal] = lambda: {"tenant": TENANT, "subject": "reviewer"}
    monkeypatch.setenv("RAG_SERVICE_TENANT_ID", TENANT)
    monkeypatch.setenv("RAG_SERVICE_URL", "http://rag:8000")
    monkeypatch.setenv("RAG_SERVICE_API_KEY", "secret")
    policy, target = str(uuid4()), str(uuid4())

    class FakeDB:
        def execute(self, statement, params):
            received.append(params)
            return self
        def scalar_one(self):
            return uuid4()

    @contextmanager
    def fake_tenant_session(tenant):
        assert tenant == TENANT
        yield FakeDB()

    received = []
    monkeypatch.setattr(main, "tenant_session", fake_tenant_session)
    client = TestClient(main.app)
    try:
        invalid = [
            {"question": "review", "workflow": "compliance"},
            {"question": "review", "workflow": "compliance", "policy_document_id": policy,
             "target_document_ids": [policy]},
            {"question": "review", "workflow": "compliance", "policy_document_id": policy,
             "target_document_ids": [target, target]},
            {"question": "review", "workflow": "research", "policy_document_id": policy,
             "target_document_ids": [target]},
        ]
        for item in invalid:
            assert client.post("/v1/agent/jobs", json=item).status_code == 422
        assert received == []
        response = client.post("/v1/agent/jobs", json={
            "question": "review", "workflow": "compliance",
            "policy_document_id": policy, "target_document_ids": [target],
        })
        assert response.status_code == 201
        assert received[0]["policy"] == policy
        assert received[0]["targets"] == [target]
        assert received[0]["tenant"] == TENANT
        monkeypatch.setenv("RAG_SERVICE_TENANT_ID", str(uuid4()))
        assert client.post("/v1/agent/jobs", json={
            "question": "review", "workflow": "compliance",
            "policy_document_id": policy, "target_document_ids": [target],
        }).status_code == 503
        assert len(received) == 1
    finally:
        main.app.dependency_overrides.clear()
