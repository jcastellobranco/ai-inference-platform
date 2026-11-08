"""Manual end-to-end smoke for ATLAS -> durable worker -> MCP agent."""
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

import httpx
import jwt


async def main():
    tenant = os.environ["AGENT_SERVICE_TENANT_ID"]
    token = jwt.encode({
        "sub": "agent-integration-smoke", "tenant_id": tenant,
        "iss": "portfolio-dev", "aud": "ai-platform",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }, os.environ["JWT_SECRET"], algorithm="HS256")
    base = os.getenv("INFERENCE_SERVICE_URL", "http://backend:8000").rstrip("/")
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
        for _ in range(40):
            try:
                response = await client.get(f"{base}/health/live")
                if response.status_code == 200:
                    break
            except httpx.RequestError:
                pass
            await asyncio.sleep(2)
        else:
            raise RuntimeError("ATLAS API unavailable")
        created = await client.post(
            f"{base}/v1/agent/jobs", headers=headers,
            json={"question": "hello integrated ATLAS MCP"},
        )
        created.raise_for_status()
        job_id = created.json()["id"]
        for _ in range(60):
            response = await client.get(f"{base}/v1/jobs/{job_id}", headers=headers)
            response.raise_for_status()
            job = response.json()
            if job["status"] in {"completed", "failed"}:
                break
            await asyncio.sleep(2)
        else:
            raise RuntimeError("Agent job did not reach terminal status")
        if job["status"] != "completed":
            raise RuntimeError(f"Agent job failed: {job.get('error')}")
        payload = json.loads(job["result"])
        assert payload["engine"] == "mcp-planned", payload
        assert payload["results"]["count"]["words"] == 4, payload
        assert payload["tool_calls"] == 1, payload
        print("SUCCESS: ATLAS JWT -> PostgreSQL queue -> worker -> Multi-Agent -> MCP stdio")
        print(f"job_id={job_id} tool_calls={payload['tool_calls']}")


if __name__ == "__main__":
    asyncio.run(main())
