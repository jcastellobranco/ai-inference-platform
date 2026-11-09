import pytest

from app.compliance_audit import build_audit_report


def test_checklist_preserves_source_and_never_claims_compliance():
    report = build_audit_report([
        {"source": "supplier.pdf", "chunk_id": "c1",
         "observation": "Cláusula de confidencialidade e proteção de dados pessoais."},
    ])
    assert report["ruleset"] == "supplier-baseline-v1"
    assert report["summary"]["requirements"] == 4
    assert report["summary"]["evidence_candidates"] == 2
    assert report["summary"]["needs_evidence_review"] == 2
    confidentiality = report["checks"][0]
    assert confidentiality["status"] == "evidence_candidate"
    assert confidentiality["evidence"][0]["source"] == "supplier.pdf"
    assert confidentiality["review_required"] is True
    assert all(check["status"] != "compliant" for check in report["checks"])


def test_no_evidence_is_not_noncompliance():
    report = build_audit_report([])
    assert all(check["status"] == "not_found_in_retrieval" for check in report["checks"])


def test_rejects_malformed_or_oversized_evidence():
    with pytest.raises(ValueError):
        build_audit_report([{"source": "x", "observation": "x"}])
    with pytest.raises(ValueError):
        build_audit_report([{"source": "x", "chunk_id": "1", "observation": "a" * 4001}])
