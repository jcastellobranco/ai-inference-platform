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
            json={"question": job["prompt"], "tenant_id": tenant, "planner": "offline", "workflow": "research" if job.get("agent_workflow") == "compliance" else job.get("agent_workflow", "tools")},
        )
        response.raise_for_status()
        body = response.json()
    if not isinstance(body, dict) or body.get("status") not in {"completed", "insufficient_evidence"}:
        raise ValueError("Invalid agent response")
    if job.get("agent_workflow") in {"research", "compliance"}:
        research = body.get("research")
        findings = research.get("findings", []) if isinstance(research, dict) else []
        if not isinstance(findings, list):
            raise ValueError("Invalid research findings")
        if job.get("agent_workflow") == "compliance":
            from .compliance_audit import build_audit_report
            body["workflow"] = "compliance"
            body["compliance"] = build_audit_report(findings)
            # A compliance screening is deliberately not a generated legal verdict.
            return json.dumps(body, ensure_ascii=False)
        # Model generation is opt-in; preserve the raw evidence if it is disabled.
        body["answer_status"] = "not_configured"
        if research and research.get("approved") and findings and os.getenv("RAG_GENERATION_ENABLED", "false").lower() == "true":
            from .generation import generate_answer
            evidence = []
            for finding in findings[:5]:
                if not isinstance(finding, dict) or not all(isinstance(finding.get(k), str) for k in ("source", "observation", "chunk_id")):
                    raise ValueError("Invalid research evidence")
                evidence.append({"source": finding["source"], "text": finding["observation"], "chunk_id": finding["chunk_id"]})
            generated = await generate_answer(job["prompt"], evidence)
            body["answer"] = generated["answer"]
            body["answer_status"] = "generated" if generated["citation_numbers"] else "insufficient_evidence"
            body["citations"] = [
                {"index": i, "source": evidence[i - 1]["source"], "chunk_id": evidence[i - 1]["chunk_id"]}
                for i in generated["citation_numbers"]
            ]
            body["generation"] = {"model": generated["model"], "usage": generated["usage"], "telemetry": generated["telemetry"]}
            body["llm_calls"] = body.get("llm_calls", 0) + generated["telemetry"]["provider_calls"]
            body["duration_ms"] = body.get("duration_ms", 0) + generated["telemetry"]["llm_ms"]
    return json.dumps(body, ensure_ascii=False)
