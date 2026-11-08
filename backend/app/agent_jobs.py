"""ATLAS worker -> private tenant-bound Multi-Agent service adapter."""
import json
import os
from urllib.parse import urlsplit

import httpx


class AgentConfigurationError(RuntimeError):
    pass


async def execute_agent(job: dict) -> str:
    url = os.getenv("AGENT_SERVICE_URL", "").rstrip("/")
    key = os.getenv("ATLAS_AGENT_SERVICE_KEY", "")
    tenant = os.getenv("AGENT_SERVICE_TENANT_ID", "")
    parsed = urlsplit(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname or
            parsed.username or parsed.password or parsed.query or parsed.fragment or
            (parsed.scheme == "http" and parsed.hostname != "agent") or
            len(key) < 32 or not tenant):
        raise AgentConfigurationError("Agent service not configured")
    if str(job["tenant_id"]) != tenant:
        raise PermissionError("Agent service tenant mismatch")
    async with httpx.AsyncClient(timeout=httpx.Timeout(90), trust_env=False) as client:
        response = await client.post(
            f"{url}/internal/v1/execute",
            headers={"x-atlas-service-key": key},
            json={"question": job["prompt"], "tenant_id": tenant, "planner": "offline"},
        )
        response.raise_for_status()
        body = response.json()
    if not isinstance(body, dict) or body.get("status") != "completed":
        raise ValueError("Invalid agent response")
    return json.dumps(body, ensure_ascii=False)
