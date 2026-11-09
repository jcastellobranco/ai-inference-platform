"""Document-scoped, deterministic compliance screening for the ATLAS worker.

The selected policy and contracts are read by UUID from the private RAG service.
No unselected document may enter the analysis. Results are screening suggestions,
not a legal finding.
"""
from __future__ import annotations

import json
import os
import re
from time import perf_counter
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx

from .compliance_audit import REQUIREMENTS, RULESET_VERSION


class MissingAuditDocument(ValueError):
    """Selection was deleted or is not visible to this tenant."""


def _rag_settings(tenant_id: str):
    target = os.getenv("RAG_SERVICE_TENANT_ID", "")
    key = os.getenv("RAG_SERVICE_API_KEY", "")
    url = os.getenv("RAG_SERVICE_URL", "").rstrip("/")
    parsed = urlsplit(url)
    if (not target or str(UUID(target)) != str(UUID(str(tenant_id))) or not key
            or parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or (parsed.scheme == "http" and parsed.hostname != "rag")):
        raise RuntimeError("Tenant-bound audit document access is not configured")
    return url, {"x-api-key": key, "x-tenant-id": target}


async def _get_document(client: httpx.AsyncClient, url: str, headers: dict, document_id: UUID):
    response = await client.get(f"{url}/v1/documents/{document_id}/content", headers=headers)
    if response.status_code == 404:
        raise MissingAuditDocument("Selected document was not found for this tenant")
    response.raise_for_status()
    document = response.json()
    if not isinstance(document, dict) or document.get("document_id") != str(document_id):
        raise ValueError("Invalid document identity in RAG response")
    chunks = document.get("chunks")
    if not isinstance(chunks, list) or len(chunks) > 512 or not isinstance(document.get("source"), str):
        raise ValueError("Invalid selected document")
    for chunk in chunks:
        if not isinstance(chunk, dict) or not isinstance(chunk.get("text"), str) or not isinstance(chunk.get("chunk_id"), str) or len(chunk["text"]) > 10000:
            raise ValueError("Invalid document chunk")
    return document


def _matches(text: str, terms: tuple[str, ...]):
    return any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.IGNORECASE) for term in terms)


def _evidence(document: dict, terms: tuple[str, ...]):
    found = []
    for chunk in document["chunks"]:
        content = chunk["text"]
        if _matches(content, terms):
            found.append({"source": document["source"], "document_id": document["document_id"],
                          "chunk_id": chunk["chunk_id"], "excerpt": content[:400]})
    return found[:3]


NEGATION_CUES = (
    "não será obrigado", "não haverá obrigação", "não há obrigação",
    "não terá obrigação", "não tem obrigação",
    "fica dispensad", "sem obrigação", "is not required",
    "no obligation", "shall not be required", "não se responsabiliza",
)


def _possible_negation(evidence: list[dict]) -> bool:
    # Conservative heuristic: flag potentially restrictive clauses for review.
    # This is not semantic or legal interpretation.
    return any(any(cue in item["excerpt"].casefold() for cue in NEGATION_CUES)
               for item in evidence)


def compare_documents(policy: dict, contracts: list[dict]):
    """Versioned lexical comparison; no inference that a clause is legally sufficient."""
    policy_checks = []
    for rule_id, label, terms in REQUIREMENTS:
        policy_checks.append((rule_id, label, terms, _evidence(policy, terms)))
    contract_reports = []
    for document in contracts:
        checks = []
        for rule_id, label, terms, policy_evidence in policy_checks:
            contract_evidence = _evidence(document, terms)
            status = ("reference_not_found" if not policy_evidence else
                      "needs_attention" if not contract_evidence or _possible_negation(contract_evidence)
                      else "evidence_to_review")
            message = {
                "reference_not_found": "No matching clause was found in the selected policy. Confirm whether this requirement applies.",
                "evidence_to_review": "A related clause was found in the contract. Verify whether it fully meets the reference policy.",
                "needs_attention": ("This clause may exclude or limit an obligation. Review its implications before approval."
                                    if contract_evidence else
                                    "No matching clause was found in this contract. Review the full document to confirm whether there is a gap."),
            }[status]
            checks.append({
                "id": rule_id, "requirement": label, "status": status, "message": message,
                "policy_evidence": policy_evidence, "contract_evidence": contract_evidence,
                "review_required": True,
            })
        contract_reports.append({
            "document_id": document["document_id"], "source": document["source"],
            "checks": checks,
            "summary": {
                "needs_attention": sum(item["status"] == "needs_attention" for item in checks),
                "evidence_to_review": sum(item["status"] == "evidence_to_review" for item in checks),
                "reference_not_found": sum(item["status"] == "reference_not_found" for item in checks),
            },
        })
    return {
        "ruleset": RULESET_VERSION, "scope": "selected_full_indexed_documents",
        "policy": {"document_id": policy["document_id"], "source": policy["source"]},
        "contracts": contract_reports,
        "summary": {
            "contracts": len(contracts),
            "needs_attention": sum(c["summary"]["needs_attention"] for c in contract_reports),
            "evidence_to_review": sum(c["summary"]["evidence_to_review"] for c in contract_reports),
            "reference_not_found": sum(c["summary"]["reference_not_found"] for c in contract_reports),
        },
        "disclaimer": "Automated document screening. A matching term does not prove contractual compliance, and a missing term does not prove noncompliance. Human review is required.",
    }


async def execute_compliance(job: dict) -> str:
    started = perf_counter()
    tenant_id = str(UUID(str(job["tenant_id"])))
    policy_id = UUID(str(job["audit_policy_document_id"]))
    target_ids = [UUID(str(value)) for value in (job["audit_target_document_ids"] or [])]
    if not 1 <= len(target_ids) <= 4 or len(set(target_ids)) != len(target_ids) or policy_id in target_ids:
        raise ValueError("Invalid selected audit documents")
    url, headers = _rag_settings(tenant_id)
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0), trust_env=False) as client:
        # Sequential, bounded reads; each is tenant-bound and fetches exactly one UUID.
        policy = await _get_document(client, url, headers, policy_id)
        contracts = []
        for document_id in target_ids:
            contracts.append(await _get_document(client, url, headers, document_id))
    retrieval_ms = round((perf_counter() - started) * 1000, 2)
    report = compare_documents(policy, contracts)
    total_ms = round((perf_counter() - started) * 1000, 2)
    result = {
        "engine": "mcp-planned", "workflow": "compliance",
        "run_id": str(uuid4()), "status": "completed", "planner": "offline",
        "results": {}, "research": None, "tool_calls": 0, "llm_calls": 0,
        "duration_ms": total_ms,
        "trace": [
            {"step": "selected-document-retrieval", "tool": "rag-document-api",
             "status": "completed", "duration_ms": retrieval_ms},
            {"step": "compliance-screening", "tool": "baseline-checklist-v1",
             "status": "completed", "duration_ms": round(total_ms - retrieval_ms, 2)},
        ],
        "compliance": report,
    }
    return json.dumps(result, ensure_ascii=False)
