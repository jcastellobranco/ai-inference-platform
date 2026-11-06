"""Manual multi-container smoke test of real RAG, inference and evaluation APIs.

Run under docker compose profile smoke. Requires model weights available to RAG.
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import httpx
import jwt

async def main():
    secret=os.environ["JWT_SECRET"]
    tenant=os.environ["RAG_SERVICE_TENANT_ID"]
    rag_url=os.environ["RAG_SERVICE_URL"].rstrip("/")
    eval_url=os.environ["EVAL_SERVICE_URL"].rstrip("/")
    backend_url=os.getenv("INFERENCE_SERVICE_URL","http://backend:8000").rstrip("/")
    rag_key=os.environ["RAG_SERVICE_API_KEY"]
    eval_key=os.environ["EVAL_SERVICE_API_KEY"]
    token=jwt.encode({
        "sub":"integration-smoke", "tenant_id":tenant,
        "iss":"portfolio-dev", "aud":"ai-platform",
        "exp":datetime.now(timezone.utc)+timedelta(minutes=10),
    },secret,algorithm="HS256")
    marker="smoke"+uuid4().hex[:12]
    source=f"{marker}.md"
    evidence=f"The unique codeword {marker} means the three-service retrieval smoke test succeeded."
    headers={"Authorization":f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=240.0,trust_env=False) as client:
        # Retry service readiness without hiding a persistent startup failure.
        for _ in range(40):
            try:
                health=await client.get(f"{rag_url}/health",timeout=5)
                eval_health=await client.get(f"{eval_url}/health",timeout=5)
                backend_health=await client.get(f"{backend_url}/health/live",timeout=5)
                if health.status_code==eval_health.status_code==backend_health.status_code==200:
                    break
            except (httpx.ConnectError,httpx.TimeoutException):
                pass
            await asyncio.sleep(3)
        else:
            raise RuntimeError("One or more services did not become healthy")
        ingested=await client.post(f"{rag_url}/v1/documents",
            headers={"x-api-key":rag_key,"x-tenant-id":tenant},
            json={"source":source,"text":evidence})
        ingested.raise_for_status()
        assert ingested.json()["chunks"]>=1
        query=f"What does codeword {marker} mean?"
        response=await client.post(f"{backend_url}/v1/rag/jobs",headers=headers,
            json={"question":query,"reference_answer":evidence})
        response.raise_for_status()
        job_id=response.json()["id"]
        for _ in range(90):
            detail=await client.get(f"{backend_url}/v1/jobs/{job_id}",headers=headers)
            detail.raise_for_status()
            job=detail.json()
            if job["status"] in ("completed","failed"):
                break
            await asyncio.sleep(2)
        else:
            raise RuntimeError(f"Job {job_id} did not finish")
        if job["status"]!="completed":
            raise RuntimeError(f"Job failed: {job.get('error')}")
        import json
        payload=json.loads(job["result"])
        assert payload["citations"], "No citations returned"
        assert any(c["source"]==source for c in payload["citations"]), payload
        assert isinstance(payload["evaluation"]["passed"],bool)
        assert "exact_match" in payload["evaluation"]["metrics"]
        print("SUCCESS: RAG ingestion -> PostgreSQL job -> worker -> evaluation API")
        print(f"job_id={job_id} mode={payload['mode']} citations={len(payload['citations'])}")
        print("evaluation=",payload["evaluation"])

if __name__=="__main__":
    asyncio.run(main())
