"""Worker metrics do not leak job/tenant identifiers or free-form status values."""
from prometheus_client import generate_latest
from app.worker_metrics import safe_type, set_queue_counts


def test_queue_metric_labels_are_bounded():
    set_queue_counts([("queued", 3), ("running", 2), ("retrying", 1),
                      ("completed", 999), ("private-tenant-id", 5)])
    metrics = generate_latest().decode()
    assert 'atlas_worker_queue_jobs{status="queued"} 3.0' in metrics
    assert 'atlas_worker_queue_jobs{status="running"} 2.0' in metrics
    assert 'atlas_worker_queue_jobs{status="retrying"} 1.0' in metrics
    assert "private-tenant-id" not in metrics


def test_unknown_job_type_is_not_exported():
    assert safe_type("rag") == "rag"
    assert safe_type("agent") == "agent"
    assert safe_type("inference") == "inference"
    assert safe_type("private-job-type") == "inference"
    assert safe_type(None) == "inference"
