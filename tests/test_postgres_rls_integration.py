"""Real PostgreSQL 17 integration tests: migrations, tenant RLS, and pooled sessions.

Requires a working Docker daemon. Run: python -m pytest tests/test_postgres_rls_integration.py -q
"""
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer

MIGRATIONS = Path(__file__).resolve().parents[1] / "backend" / "migrations"
TENANT_A = "11111111-1111-4111-8111-111111111111"
TENANT_B = "22222222-2222-4222-8222-222222222222"


@pytest.fixture(scope="module")
def postgres_db():
    with PostgresContainer("postgres:17", dbname="platform", username="app", password="app") as container:
        # Run the same migration sequence as docker-compose.fullstack.yml, as owner.
        owner_url = container.get_connection_url().replace("postgresql+psycopg2://", "postgresql://").replace("postgresql+psycopg://", "postgresql://")
        with psycopg.connect(owner_url, autocommit=True) as conn:
            for migration in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
                conn.execute(migration.read_text(encoding="utf-8"))
        runtime_url = owner_url.replace("://app:app@", "://platform_runtime:local-development-only@")
        worker_url = owner_url.replace("://app:app@", "://platform_worker:local-worker-development-only@")
        runtime_engine = create_engine(runtime_url, pool_size=1, max_overflow=0)
        worker_engine = create_engine(worker_url, pool_size=1, max_overflow=0)
        try:
            yield runtime_engine, worker_engine
        finally:
            runtime_engine.dispose()
            worker_engine.dispose()


def _tenant(conn, tenant_id):
    conn.execute(text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant": tenant_id})


def _create_job(conn, tenant_id):
    return conn.execute(
        text("INSERT INTO jobs (tenant_id, prompt, status, created_by) "
             "VALUES (:tenant, 'integration test', 'queued', 'pytest') RETURNING id"),
        {"tenant": tenant_id},
    ).scalar_one()


def test_migrations_create_expected_schema_and_restricted_roles(postgres_db):
    runtime, _ = postgres_db
    with runtime.connect() as conn:
        columns = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'jobs'"
        )).scalars().all()
        assert {"tenant_id", "status", "agent_workflow", "job_type", "lease_token"} <= set(columns)
        assert conn.execute(text(
            "SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user"
        )).scalar_one() is False


def test_tenant_cannot_read_or_modify_other_tenant_job(postgres_db):
    runtime, _ = postgres_db
    with runtime.begin() as conn:
        _tenant(conn, TENANT_A)
        job_a = _create_job(conn, TENANT_A)
    with runtime.begin() as conn:
        _tenant(conn, TENANT_B)
        job_b = _create_job(conn, TENANT_B)
        visible = conn.execute(text("SELECT id FROM jobs WHERE id=:id"), {"id": job_a}).first()
        assert visible is None
        assert conn.execute(
            text("UPDATE jobs SET prompt='hijacked' WHERE id=:id RETURNING id"),
            {"id": job_a},
        ).first() is None
        assert conn.execute(text("SELECT id FROM jobs WHERE id=:id"), {"id": job_b}).scalar_one() == job_b
    with runtime.begin() as conn:
        _tenant(conn, TENANT_A)
        assert conn.execute(text("SELECT prompt FROM jobs WHERE id=:id"), {"id": job_a}).scalar_one() == "integration test"


def test_tenant_cannot_insert_for_another_tenant(postgres_db):
    runtime, _ = postgres_db
    with pytest.raises(Exception) as exc:
        with runtime.begin() as conn:
            _tenant(conn, TENANT_A)
            _create_job(conn, TENANT_B)
    assert "row-level security" in str(exc.value).lower()


def test_tenant_context_does_not_leak_through_connection_pool(postgres_db):
    runtime, _ = postgres_db
    with runtime.begin() as conn:
        _tenant(conn, TENANT_A)
        _create_job(conn, TENANT_A)
    # Reuse same pooled physical connection, but a new transaction.
    with runtime.begin() as conn:
        assert conn.execute(text("SELECT current_setting('app.tenant_id', true)")).scalar_one() in ("", None)
        assert conn.execute(text("SELECT count(*) FROM jobs")).scalar_one() == 0


def test_worker_role_has_explicit_cross_tenant_read_policy(postgres_db):
    runtime, worker = postgres_db
    with runtime.begin() as conn:
        _tenant(conn, TENANT_A)
        job = _create_job(conn, TENANT_A)
    with worker.begin() as conn:
        assert conn.execute(text("SELECT id FROM jobs WHERE id=:id"), {"id": job}).scalar_one() == job
