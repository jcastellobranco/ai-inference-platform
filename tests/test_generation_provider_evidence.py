"""Provider-level regression: references to omitted chunks must fail."""
import asyncio
import json
import httpx
import pytest
from app.generation import GroundingError, generate_answer


def test_provider_cannot_cite_sixth_omitted_chunk(monkeypatch):
    monkeypatch.setenv("GENERATION_API_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("GENERATION_API_KEY", "test-only")
    monkeypatch.setenv("GENERATION_MODEL", "test-model")
    calls = []

    def respond(request):
        payload = json.loads(request.content)
        calls.append(payload)
        return httpx.Response(200, json={"choices":[{"message":{"content":"Unsupported claim [6]"}}]})

    evidence = [{"source":f"doc{i}","chunk_id":str(i),"text":f"Evidence {i}"} for i in range(1,7)]
    with pytest.raises(GroundingError):
        asyncio.run(generate_answer("Question?", evidence, transport=httpx.MockTransport(respond)))
    assert len(calls) == 2  # initial answer + bounded repair
    assert "doc5" in calls[0]["messages"][1]["content"]
    assert "doc6" not in calls[0]["messages"][1]["content"]
