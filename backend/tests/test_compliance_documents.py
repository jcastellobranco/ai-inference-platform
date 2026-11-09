"""Selected-document compliance: business output, tenant isolation and evidence provenance."""
import asyncio
import json
from uuid import uuid4

import httpx
import pytest

from app.compliance_documents import compare_documents, execute_compliance, MissingAuditDocument

TENANT = "11111111-1111-4111-8111-111111111111"


def document(id_, source, text):
    return {"document_id": str(id_), "source": source,
            "chunks": [{"chunk_id": str(uuid4()), "text": text, "ordinal": 0}]}


def test_each_contract_is_separate_and_never_uses_policy_as_contract_evidence():
    policy_id, good_id, bad_id = uuid4(), uuid4(), uuid4()
    policy = document(policy_id, "policy.pdf",
                      "Confidencialidade. Notificação de incidente de segurança. Proteção de dados pessoais. Rescisão.")
    good = document(good_id, "supplier-good.pdf",
                    "Cláusula de confidencialidade e proteção de dados pessoais. Notificação de incidente de segurança. Rescisão.")
    bad = document(bad_id, "supplier-bad.pdf",
                   "O fornecedor não terá obrigação de notificar incidente de segurança. Confidencialidade.")
    result = compare_documents(policy, [good, bad])
    assert result["summary"]["contracts"] == 2
    assert result["contracts"][0]["summary"]["needs_attention"] == 0
    assert result["contracts"][1]["summary"]["needs_attention"] >= 2
    assert result["policy"]["source"] == "policy.pdf"
    assert all(e["document_id"] == str(bad_id) for check in result["contracts"][1]["checks"]
               for e in check["contract_evidence"])
    assert all(e["document_id"] == str(policy_id) for check in result["contracts"][1]["checks"]
               for e in check["policy_evidence"])
    assert all(check["review_required"] for contract in result["contracts"] for check in contract["checks"])


def test_missing_reference_is_not_a_contract_violation():
    policy = document(uuid4(), "policy.pdf", "Política sobre horário de atendimento.")
    contract = document(uuid4(), "contract.pdf", "Confidencialidade, LGPD e rescisão.")
    report = compare_documents(policy, [contract])
    assert report["contracts"][0]["summary"]["reference_not_found"] == 4
    assert report["contracts"][0]["summary"]["needs_attention"] == 0


def test_scoped_worker_reads_exact_ids_and_rejects_missing_target(monkeypatch):
    policy_id, target_id, unselected_id = uuid4(), uuid4(), uuid4()
    urls = []

    def handle(request):
        urls.append(str(request.url))
        assert request.headers["x-tenant-id"] == TENANT
        assert request.headers["x-api-key"] == "secret"
        if str(request.url).endswith(str(policy_id) + "/content"):
            return httpx.Response(200, json=document(policy_id, "policy.pdf", "Confidencialidade"))
        if str(request.url).endswith(str(target_id) + "/content"):
            return httpx.Response(200, json=document(target_id, "target.pdf", "Confidencialidade"))
        return httpx.Response(404)

    real_client = httpx.AsyncClient
    monkeypatch.setattr("app.compliance_documents.httpx.AsyncClient",
                        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))
    monkeypatch.setenv("RAG_SERVICE_URL", "http://rag:8000")
    monkeypatch.setenv("RAG_SERVICE_TENANT_ID", TENANT)
    monkeypatch.setenv("RAG_SERVICE_API_KEY", "secret")
    job = {"tenant_id": TENANT, "audit_policy_document_id": policy_id,
           "audit_target_document_ids": [target_id]}
    result = json.loads(asyncio.run(execute_compliance(job)))
    assert result["compliance"]["contracts"][0]["source"] == "target.pdf"
    assert len(urls) == 2
    assert all(str(unselected_id) not in url for url in urls)

    with pytest.raises(MissingAuditDocument):
        asyncio.run(execute_compliance({**job, "audit_target_document_ids": [unselected_id]}))
    with pytest.raises(RuntimeError, match="Tenant-bound"):
        asyncio.run(execute_compliance({**job, "tenant_id": str(uuid4())}))


def test_invalid_selection_does_not_contact_upstream(monkeypatch):
    job = {"tenant_id": TENANT, "audit_policy_document_id": uuid4()}
    job["audit_target_document_ids"] = [job["audit_policy_document_id"]]
    with pytest.raises(ValueError, match="Invalid selected"):
        asyncio.run(execute_compliance(job))
