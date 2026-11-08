import asyncio
import json
from uuid import UUID

import httpx
import pytest

from app.agent_jobs import AgentConfigurationError, execute_agent


def test_agent_adapter_rejects_unconfigured(monkeypatch):
    monkeypatch.delenv("AGENT_SERVICE_URL", raising=False)
    with pytest.raises(AgentConfigurationError):
        asyncio.run(execute_agent({"tenant_id": UUID("11111111-1111-4111-8111-111111111111"), "prompt": "hello"}))


def test_agent_adapter_rejects_wrong_tenant(monkeypatch):
    monkeypatch.setenv("AGENT_SERVICE_URL", "http://agent:8000")
    monkeypatch.setenv("ATLAS_AGENT_SERVICE_KEY", "x" * 40)
    monkeypatch.setenv("AGENT_SERVICE_TENANT_ID", "11111111-1111-4111-8111-111111111111")
    with pytest.raises(PermissionError):
        asyncio.run(execute_agent({"tenant_id": UUID("22222222-2222-4222-8222-222222222222"), "prompt": "hello"}))
