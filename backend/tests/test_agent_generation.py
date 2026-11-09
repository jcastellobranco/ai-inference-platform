"""Research answer synthesis uses tenant-bound evidence and is opt-in."""
import asyncio
import json

from app import agent_jobs


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {
            "engine": "mcp-planned", "status": "completed", "planner": "offline",
            "results": {"count": {"words": 4}}, "trace": [], "tool_calls": 1,
            "llm_calls": 0, "duration_ms": 12,
            "research": {"approved": True, "status": "reviewed",
                         "findings": [{"source": "rules.pdf", "chunk_id": "c1",
                                       "observation": "Athletes must follow the rules."}]},
        }


class FakeClient:
    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def post(self, *args, **kwargs):
        return FakeResponse()


def test_research_generates_cited_answer_when_enabled(monkeypatch):
    monkeypatch.setenv("AGENT_SERVICE_URL", "http://agent:8000")
    monkeypatch.setenv("ATLAS_AGENT_SERVICE_KEY", "x" * 40)
    monkeypatch.setenv("AGENT_SERVICE_TENANT_ID", "11111111-1111-4111-8111-111111111111")
    monkeypatch.setenv("RAG_GENERATION_ENABLED", "true")
    monkeypatch.setattr(agent_jobs.httpx, "AsyncClient", FakeClient)

    async def fake_generate(question, evidence):
        assert question == "What must athletes follow?"
        assert evidence[0]["text"] == "Athletes must follow the rules."
        return {"answer": "They must follow the rules [1].", "citation_numbers": [1],
                "model": "test-model", "usage": {},
                "telemetry": {"provider_calls": 1, "llm_ms": 5}}

    from app import generation
    monkeypatch.setattr(generation, "generate_answer", fake_generate)
    output = asyncio.run(agent_jobs.execute_agent({
        "tenant_id": "11111111-1111-4111-8111-111111111111",
        "prompt": "What must athletes follow?", "agent_workflow": "research",
    }))
    result = json.loads(output)
    assert result["answer_status"] == "generated"
    assert result["citations"][0]["chunk_id"] == "c1"
    assert result["llm_calls"] == 1
    assert result["research"]["findings"][0]["observation"] == "Athletes must follow the rules."


def test_research_without_generation_keeps_evidence(monkeypatch):
    monkeypatch.setenv("AGENT_SERVICE_URL", "http://agent:8000")
    monkeypatch.setenv("ATLAS_AGENT_SERVICE_KEY", "x" * 40)
    monkeypatch.setenv("AGENT_SERVICE_TENANT_ID", "11111111-1111-4111-8111-111111111111")
    monkeypatch.delenv("RAG_GENERATION_ENABLED", raising=False)
    monkeypatch.setattr(agent_jobs.httpx, "AsyncClient", FakeClient)
    result = json.loads(asyncio.run(agent_jobs.execute_agent({
        "tenant_id": "11111111-1111-4111-8111-111111111111",
        "prompt": "What must athletes follow?", "agent_workflow": "research",
    })))
    assert result["answer_status"] == "not_configured"
    assert "answer" not in result
