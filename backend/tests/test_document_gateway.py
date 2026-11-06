"""Document BFF guards against tenant bypass and service-key exposure."""
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException

from app import document_gateway


def test_foreign_tenant_rejected_before_network(monkeypatch):
    monkeypatch.setenv("RAG_SERVICE_TENANT_ID", "11111111-1111-4111-8111-111111111111")
    monkeypatch.setenv("RAG_SERVICE_URL", "http://rag:8000")
    monkeypatch.setenv("RAG_SERVICE_API_KEY", "internal-key")
    with pytest.raises(HTTPException) as exc:
        document_gateway._settings({"tenant": "22222222-2222-4222-8222-222222222222"})
    assert exc.value.status_code == 403


def test_gateway_only_uses_configured_service_key(monkeypatch):
    monkeypatch.setenv("RAG_SERVICE_TENANT_ID", "11111111-1111-4111-8111-111111111111")
    monkeypatch.setenv("RAG_SERVICE_URL", "http://rag:8000")
    monkeypatch.setenv("RAG_SERVICE_API_KEY", "internal-key")

    def fake_request(self, method, url, **kwargs):
        assert method == "GET"
        assert url == "http://rag:8000/v1/documents"
        assert kwargs["headers"]["x-api-key"] == "internal-key"
        assert kwargs["headers"]["x-tenant-id"] == "11111111-1111-4111-8111-111111111111"
        return httpx.Response(200, request=httpx.Request(method, url), json={"items": []})

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    result = document_gateway.list_documents({"tenant": "11111111-1111-4111-8111-111111111111"})
    assert result == {"items": []}


def test_upstream_failures_do_not_leak_internal_response(monkeypatch):
    monkeypatch.setenv("RAG_SERVICE_TENANT_ID", "11111111-1111-4111-8111-111111111111")
    monkeypatch.setenv("RAG_SERVICE_URL", "http://rag:8000")
    monkeypatch.setenv("RAG_SERVICE_API_KEY", "internal-key")

    def fail(self, method, url, **kwargs):
        return httpx.Response(500, request=httpx.Request(method, url), text="private postgres trace")

    monkeypatch.setattr(httpx.Client, "request", fail)
    with pytest.raises(HTTPException) as exc:
        document_gateway.list_documents({"tenant": "11111111-1111-4111-8111-111111111111"})
    assert exc.value.status_code == 502
    assert "postgres" not in exc.value.detail
