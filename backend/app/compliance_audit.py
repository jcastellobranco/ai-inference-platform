"""Conservative evidence-based compliance screening.

This is a screening report, NOT a legal compliance determination. Requirements are
fixed and versioned; evidence matches are candidates for human verification.
"""
from __future__ import annotations

import re
from typing import Any

RULESET_VERSION = "supplier-baseline-v1"
REQUIREMENTS = (
    ("confidentiality", "Confidentiality obligations", ("confidencialidade", "sigilo", "confidentiality", "non-disclosure")),
    ("incident_notification", "Security incident notification", ("incidente de segurança", "notificação de incidente", "security incident", "breach notification")),
    ("data_protection", "Personal data protection", ("dados pessoais", "proteção de dados", "lgpd", "personal data", "data protection")),
    ("termination", "Termination conditions", ("rescisão", "resolução contratual", "termination", "cancelamento do contrato")),
)

def build_audit_report(findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Screen up to five tenant-scoped retrieved excerpts against an explicit checklist.

    A lexical hit never proves a requirement is fulfilled. No hit only means
    not located in retrieved excerpts, not absent from the full documents.
    """
    if not isinstance(findings, list) or len(findings) > 10:
        raise ValueError("Invalid audit evidence")
    evidence = []
    for item in findings[:5]:
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in ("source", "observation", "chunk_id")):
            raise ValueError("Invalid audit evidence item")
        if len(item["source"]) > 256 or len(item["observation"]) > 4000 or len(item["chunk_id"]) > 128:
            raise ValueError("Audit evidence exceeds bounds")
        evidence.append(item)
    checks = []
    for rule_id, label, terms in REQUIREMENTS:
        matches = []
        for item in evidence:
            excerpt = item["observation"]
            if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", excerpt, flags=re.IGNORECASE) for term in terms):
                matches.append({
                    "source": item["source"], "chunk_id": item["chunk_id"],
                    "excerpt": excerpt[:350],
                })
        checks.append({
            "id": rule_id, "requirement": label,
            "status": "evidence_candidate" if matches else "not_found_in_retrieval",
            "evidence": matches[:3],
            "review_required": True,
        })
    return {
        "ruleset": RULESET_VERSION,
        "scope": "retrieved_excerpts_only",
        "disclaimer": "Screening only. Matches do not establish compliance; missing matches do not establish noncompliance. Human review of complete documents is required.",
        "documents_retrieved": len(set(item["source"] for item in evidence)),
        "chunks_reviewed": len(evidence),
        "checks": checks,
        "summary": {
            "requirements": len(checks),
            "evidence_candidates": sum(check["status"] == "evidence_candidate" for check in checks),
            "needs_evidence_review": sum(check["status"] == "not_found_in_retrieval" for check in checks),
        },
    }
