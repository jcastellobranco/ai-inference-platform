"""PostgreSQL RLS integration tests against a non-owner runtime role."""
import os
import pytest
from sqlalchemy import create_engine, text

A = "11111111-1111-4111-8111-111111111111"
B = "22222222-2222-4222-8222-222222222222"

@pytest.fixture
def engine():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated PostgreSQL runtime-role DSN")
    engine = create_engine(url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()

def test_cross_tenant_reads_and_inserts(engine):
    with engine.connect() as connection:
        role, owner, bypass = connection.execute(text(
            "SELECT current_user, pg_get_userbyid(c.relowner), r.rolbypassrls "
            "FROM pg_class c CROSS JOIN pg_roles r WHERE c.oid='jobs'::regclass AND r.rolname=current_user"
        )).one()
        assert role != owner and not bypass, "Must test non-owner non-BYPASSRLS runtime role"
        connection.rollback()
        with connection.begin():
            connection.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": A})
            job = connection.execute(text(
                "INSERT INTO jobs(tenant_id,prompt,status,created_by) "
                "VALUES (:t,'rls integration probe','queued','test') RETURNING id"
            ), {"t": A}).scalar_one()
        try:
            with connection.begin():
                connection.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": B})
                assert connection.execute(text("SELECT count(*) FROM jobs WHERE id=:id"), {"id": job}).scalar_one() == 0
                with pytest.raises(Exception):
                    with connection.begin_nested():
                        connection.execute(text(
                            "INSERT INTO jobs(tenant_id,prompt,status,created_by) "
                            "VALUES (:t,'should be blocked','queued','test')"
                        ), {"t": A})
        finally:
            with connection.begin():
                connection.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": A})
                connection.execute(text("DELETE FROM jobs WHERE id=:id"), {"id": job})
