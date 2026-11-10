"""Worker-only Prometheus metrics with fixed labels and no job/tenant payloads."""
from prometheus_client import Counter, Gauge, Histogram

JOB_RESULTS = Counter(
    "atlas_worker_jobs_total", "Worker job processing results",
    ["job_type", "outcome"],
)
JOB_DURATION = Histogram(
    "atlas_worker_job_duration_seconds", "Worker processing time (not queue wait)",
    ["job_type"],
)
QUEUE_JOBS = Gauge(
    "atlas_worker_queue_jobs", "Current PostgreSQL jobs by active state",
    ["status"],
)
FENCING_CONFLICTS = Counter(
    "atlas_worker_fencing_conflicts_total", "Stale worker result writes rejected",
)

VALID_TYPES = frozenset(("rag", "agent", "inference"))
ACTIVE_STATES = ("queued", "running", "retrying")


def safe_type(value: str | None) -> str:
    return value if value in VALID_TYPES else "inference"


def set_queue_counts(rows) -> None:
    """Only known active statuses become metric labels."""
    counts = {str(status): int(count) for status, count in rows
              if str(status) in ACTIVE_STATES}
    for status in ACTIVE_STATES:
        QUEUE_JOBS.labels(status=status).set(counts.get(status, 0))
