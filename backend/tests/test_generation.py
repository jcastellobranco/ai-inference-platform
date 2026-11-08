"""Provider is mocked: no external tokens or model downloads in CI."""
import asyncio
import json
import httpx
import pytest
from app.generation import generate_answer, validate_citations, GroundingError, grounded_messages
from app import rag_jobs

EVIDENCE=[{"source":"guide.md","chunk_id":"c1","text":"Kubernetes schedules pods onto nodes."}]

def test_evidence_prompt_and_citation_validator():
    messages=grounded_messages("Where do pods go?",EVIDENCE)
    assert "untrusted" in messages[1]["content"]
    assert "guide.md#c1" in messages[1]["content"]
    assert validate_citations("They are scheduled on nodes [1].",1)==[1]
    with pytest.raises(GroundingError):
        validate_citations("They go to Mars.",1)
    with pytest.raises(GroundingError):
        validate_citations("They go to Mars [2].",1)

def test_generation_api_contract(monkeypatch):
    monkeypatch.setenv("GENERATION_API_URL","https://api.openai.com/v1")
    monkeypatch.setenv("GENERATION_API_KEY","model-secret")
    monkeypatch.setenv("GENERATION_MODEL","test-model")
    def handler(req):
        assert req.headers["Authorization"]=="Bearer model-secret"
        assert str(req.url)=="https://api.openai.com/v1/chat/completions"
        payload=json.loads(req.content)
        assert payload["model"]=="test-model"
        assert payload["max_completion_tokens"]==500
        assert payload["messages"][0]["role"]=="system"
        return httpx.Response(200,json={"choices":[{"message":{"content":"Pods run on nodes [1]."}}]})
    result=asyncio.run(generate_answer("Where?",EVIDENCE,
                                      transport=httpx.MockTransport(handler)))
    assert result["answer"]=="Pods run on nodes [1]."
    assert result["citation_numbers"]==[1]
    assert result["model"]=="test-model"
    assert result["telemetry"]["provider_calls"]==1
    assert result["telemetry"]["repair_attempted"] is False
    assert result["usage"]=={"input_tokens":None,"output_tokens":None}

def test_generation_refuses_unattributed_output(monkeypatch):
    monkeypatch.setenv("GENERATION_API_URL","https://api.openai.com/v1")
    monkeypatch.setenv("GENERATION_API_KEY","model-secret")
    monkeypatch.setenv("GENERATION_MODEL","test-model")
    transport=httpx.MockTransport(lambda req:httpx.Response(
        200,json={"choices":[{"message":{"content":"I know everything."}}]}))
    with pytest.raises(GroundingError,match="citations"):
        asyncio.run(generate_answer("Where?",EVIDENCE,transport=transport))

def test_rag_job_opt_in_generation(monkeypatch):
    async def retrieve(question, tenant):
        return EVIDENCE
    async def generate(question,evidence):
        return {"answer":"Pods on nodes [1].","citation_numbers":[1],"model":"test-model"}
    monkeypatch.setattr(rag_jobs,"retrieve",retrieve)
    monkeypatch.setattr(rag_jobs,"generate_answer",generate)
    monkeypatch.setenv("RAG_GENERATION_ENABLED","true")
    result=json.loads(asyncio.run(rag_jobs.execute_rag({
        "id":"test","tenant_id":"11111111-1111-4111-8111-111111111111",
        "prompt":"Where?","reference_answer":None
    })))
    assert result["mode"]=="grounded_generation"
    assert result["model"]=="test-model"
    assert result["citations"]==[{"source":"guide.md","chunk_id":"c1"}]
    assert result["answer"]=="Pods on nodes [1]."

def test_no_evidence_must_not_call_model(monkeypatch):
    async def retrieve(question,tenant):
        return []
    async def never(*args):
        raise AssertionError("Provider must not be called without evidence")
    monkeypatch.setattr(rag_jobs,"retrieve",retrieve)
    monkeypatch.setattr(rag_jobs,"generate_answer",never)
    monkeypatch.setenv("RAG_GENERATION_ENABLED","true")
    result=json.loads(asyncio.run(rag_jobs.execute_rag({
        "id":"test","tenant_id":"11111111-1111-4111-8111-111111111111",
        "prompt":"Unknown","reference_answer":None
    })))
    assert result["mode"]=="insufficient_evidence"
    assert result["citations"]==[]

def test_generation_rejects_unapproved_provider_before_network(monkeypatch):
    monkeypatch.setenv("GENERATION_API_URL", "https://models.example.test/v1")
    monkeypatch.setenv("GENERATION_API_KEY", "model-secret")
    monkeypatch.setenv("GENERATION_MODEL", "test-model")
    def unexpected_request(req):
        raise AssertionError("Disallowed provider must never be contacted")
    with pytest.raises(RuntimeError, match="api.openai.com"):
        asyncio.run(generate_answer("Where?", EVIDENCE,
                                    transport=httpx.MockTransport(unexpected_request)))
