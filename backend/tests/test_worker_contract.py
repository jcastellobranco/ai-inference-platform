"""Worker contract tests independent of PostgreSQL."""
import pytest
from app.worker import make_session

def test_worker_requires_dedicated_database_url(monkeypatch):
    monkeypatch.delenv("WORKER_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="WORKER_DATABASE_URL"):
        make_session()
