"""Service boundary tests: tenant binding, auth, payload validation and extractive output."""
import asyncio
import json
from uuid import uuid4
import httpx
import pytest
from app import rag_client, rag_jobs

ALLOWED = "11111111-1111-4111-8111-111111111111"
FOREIGN = "22222222-2222-4222-8222-222222222222"

def configure(monkeypatch):
    monkeypatch.setenv("RAG_SERVICE_TENANT_ID", ALLOWED)
    monkeypatch.setenv("RAG_SERVICE_URL", "https://rag.example.test")
    monkeypatch.setenv("RAG_SERVICE_API_KEY", "rag-test-key")
    monkeypatch.setenv("EVAL_SERVICE_URL", "https://eval.example.test")
    monkeypatch.setenv("EVAL_SERVICE_API_KEY", "eval-test-key")

def test_foreign_tenant_is_blocked_before_network(monkeypatch):
    configure(monkeypatch)
    def forbidden(request):
        raise AssertionError("No outbound request is allowed")
    transport = httpx.MockTransport(forbidden)
    with pytest.raises(PermissionError, match="not enabled"):
        asyncio.run(rag_client.retrieve("question", FOREIGN, transport=transport))

def test_retrieval_uses_server_bound_tenant_and_key(monkeypatch):
    configure(monkeypatch)
    def handler(request):
        assert str(request.url) == "https://rag.example.test/v1/search"
        assert request.headers["x-api-key"] == "rag-test-key"
        assert request.headers["x-tenant-id"] == ALLOWED
        body = json.loads(request.content)
        assert body == {"question":"Kubernetes", "limit":5}
        return httpx.Response(200, json={"citations":[
            {"chunk_id":"c1", "source":"manual.md", "text":"Kubernetes schedules pods", "score":1}
        ]})
    result = asyncio.run(rag_client.retrieve("Kubernetes", ALLOWED, transport=httpx.MockTransport(handler)))
    assert result == [{"chunk_id":"c1", "source":"manual.md", "text":"Kubernetes schedules pods"}]

def test_rag_contract_rejects_invalid_response(monkeypatch):
    configure(monkeypatch)
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"citations":"not-a-list"}))
    with pytest.raises(ValueError, match="Invalid RAG response"):
        asyncio.run(rag_client.retrieve("question", ALLOWED, transport=transport))

def test_evaluation_auth_and_contract(monkeypatch):
    configure(monkeypatch)
    def handler(request):
        assert request.headers["x-api-key"] == "eval-test-key"
        payload = json.loads(request.content)
        assert payload["cases"][0]["reference"] == "expected"
        return httpx.Response(200, json={"passed":False,"failures":["exact_match below 0.8"],
                                          "metrics":{"exact_match":0}})
    result=asyncio.run(rag_client.evaluate_answer("retrieved","expected","job-1",
                  transport=httpx.MockTransport(handler)))
    assert result["passed"] is False
    assert result["metrics"]["exact_match"] == 0

def test_rag_job_is_extractive_and_cited(monkeypatch):
    async def fake_retrieve(question, tenant_id):
        assert question == "Where are pods scheduled?"
        assert tenant_id == ALLOWED
        return [{"source":"manual.md","chunk_id":"c1","text":"Pods are scheduled on nodes."}]
    async def fake_evaluate(answer, reference, job_id, *, latency_ms):
        assert latency_ms >= 0
        assert answer == "Pods are scheduled on nodes."
        return {"passed":True,"metrics":{"exact_match":1}, "failures":[]}
    monkeypatch.setattr(rag_jobs, "retrieve", fake_retrieve)
    monkeypatch.setattr(rag_jobs, "evaluate_answer", fake_evaluate)
    job={"id":str(uuid4()),"tenant_id":ALLOWED,"prompt":"Where are pods scheduled?",
         "reference_answer":"Pods are scheduled on nodes."}
    result=json.loads(asyncio.run(rag_jobs.execute_rag(job)))
    assert result["mode"] == "extractive_first_chunk"
    assert result["answer_status"] == "answered"
    assert result["retrieval"]["chunks_found"] == 1
    assert result["citations"] == [{"source":"manual.md","chunk_id":"c1"}]
    assert result["evaluation"]["passed"] is True

def test_empty_retrieval_does_not_hallucinate(monkeypatch):
    async def empty(question, tenant_id):
        return []
    monkeypatch.setattr(rag_jobs,"retrieve",empty)
    result=json.loads(asyncio.run(rag_jobs.execute_rag({
        "id":str(uuid4()),"tenant_id":ALLOWED,"prompt":"unknown","reference_answer":None
    })))
    assert result["mode"] == "insufficient_evidence"
    assert result["answer_status"] == "insufficient_evidence"
    assert result["retrieval"]["chunks_found"] == 0
    assert result["citations"] == []
    assert result["evaluation"] is None


def test_generated_refusal_has_distinct_status(monkeypatch):
    monkeypatch.setenv("RAG_GENERATION_ENABLED", "true")
    async def found(question, tenant_id):
        return [{"source": "rules.pdf", "chunk_id": "c1", "text": "Only official schedule is covered."}]
    async def refusal(question, evidence):
        return {"answer": "Insufficient retrieved evidence to answer.",
                "citation_numbers": [], "model": "mock", "usage": {"input_tokens": 10, "output_tokens": 2}}
    monkeypatch.setattr(rag_jobs, "retrieve", found)
    monkeypatch.setattr(rag_jobs, "generate_answer", refusal)
    result = json.loads(asyncio.run(rag_jobs.execute_rag({
        "id": str(uuid4()), "tenant_id": ALLOWED, "prompt": "Can I wear my own clothes?",
        "reference_answer": None,
    })))
    assert result["mode"] == "insufficient_evidence"
    assert result["answer_status"] == "insufficient_evidence"
    assert result["retrieval"]["chunks_found"] == 1
    assert result["citations"] == []
