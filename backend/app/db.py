"""Tenant-aware database sessions. Never accept tenant IDs from request bodies."""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://app:app@localhost:5432/platform")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=5)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

@contextmanager
def tenant_session(tenant_id: str):
    """SET LOCAL is transaction scoped and safe with pooled connections."""
    with SessionLocal() as session:
        with session.begin():
            session.execute(text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant": tenant_id})
            yield session
