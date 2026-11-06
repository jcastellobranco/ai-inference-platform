"""Service-to-service retrieval and evaluation with explicit tenant binding.

The current RAG HTTP service is single-tenant. Reject other tenants before any
network request; the x-tenant-id header is defense in depth, not authorization.
"""
import os
from uuid import UUID
import httpx

class IntegrationConfigurationError(RuntimeError):
    pass

def _service_settings(tenant_id: str):
    target = os.getenv("RAG_SERVICE_TENANT_ID", "")
    url = os.getenv("RAG_SERVICE_URL", "").rstrip("/")
    key = os.getenv("RAG_SERVICE_API_KEY", "")
    if not target or not url or not key:
        raise IntegrationConfigurationError("RAG service URL, key and allowed tenant must be configured")
    if str(UUID(target)) != str(UUID(str(tenant_id))):
        raise PermissionError("RAG integration not enabled for this tenant")
    if not url.startswith(("https://", "http://")):
        raise IntegrationConfigurationError("RAG service URL must be HTTP(S)")
    return url, key, str(UUID(target))

async def retrieve(question: str, tenant_id: str, *, transport=None) -> list[dict]:
    if not question or len(question) > 2000:
        raise ValueError("RAG question must have 1..2000 characters")
    url, key, allowed_tenant = _service_settings(tenant_id)
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0), transport=transport, trust_env=False) as client:
        response = await client.post(
            f"{url}/v1/search", headers={"x-api-key": key, "x-tenant-id": allowed_tenant},
            json={"question": question, "limit": 5}
        )
        response.raise_for_status()
        data = response.json()
    citations = data.get("citations")
    if not isinstance(citations, list):
        raise ValueError("Invalid RAG response: missing citations")
    result = []
    for hit in citations[:5]:
        if not isinstance(hit, dict) or not all(isinstance(hit.get(k), str) for k in ("chunk_id", "source", "text")):
            raise ValueError("Invalid RAG citation")
        result.append({"chunk_id": hit["chunk_id"][:128], "source": hit["source"][:256],
                       "text": hit["text"][:4000]})
    return result

async def evaluate_answer(answer: str, reference: str, job_id: str, *, transport=None) -> dict:
    url = os.getenv("EVAL_SERVICE_URL", "").rstrip("/")
    key = os.getenv("EVAL_SERVICE_API_KEY", "")
    if not url or not key:
        raise IntegrationConfigurationError("Evaluation service URL and key are required")
    if not url.startswith(("https://", "http://")):
        raise IntegrationConfigurationError("Evaluation service URL must be HTTP(S)")
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0), transport=transport, trust_env=False) as client:
        response = await client.post(
            f"{url}/v1/evaluate", headers={"x-api-key": key},
            json={"cases": [{"id": job_id, "prediction": answer, "reference": reference, "latency_ms": 0}]}
        )
        response.raise_for_status()
        body = response.json()
    if not isinstance(body.get("passed"), bool) or not isinstance(body.get("metrics"), dict):
        raise ValueError("Invalid evaluation response")
    return {"passed": body["passed"], "metrics": body["metrics"], "failures": body.get("failures", [])}
