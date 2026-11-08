"""FastAPI API demonstrating JWT tenant claims and PostgreSQL RLS."""
import os
from uuid import UUID
import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import text
from .db import tenant_session

app = FastAPI(title="Multi-Tenant AI Platform", version="0.1.0")
bearer = HTTPBearer()
ISSUER = os.environ.get("JWT_ISSUER", "portfolio-dev")
AUDIENCE = os.environ.get("JWT_AUDIENCE", "ai-platform")
SECRET = os.environ.get("JWT_SECRET")

class JobCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)

class AgentJobCreate(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    workflow: str = Field(default='tools', pattern='^(tools|research)


class RagJobCreate(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    reference_answer: str | None = Field(default=None, min_length=1, max_length=16000)

def principal(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not SECRET or len(SECRET) < 32:
        raise HTTPException(503, "JWT secret not configured securely")
    try:
        claims = jwt.decode(credentials.credentials, SECRET, algorithms=["HS256"], issuer=ISSUER, audience=AUDIENCE, options={"require": ["sub", "tenant_id", "exp", "iss", "aud"]})
        tenant = str(UUID(claims["tenant_id"]))
        return {"subject": claims["sub"], "tenant": tenant}
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, "Invalid token")

@app.get("/health/live")
def live():
    return {"status": "ok"}

@app.get("/v1/jobs")
def list_jobs(identity=Depends(principal)):
    with tenant_session(identity["tenant"]) as db:
        rows = db.execute(text("SELECT id, prompt, status, result, error, attempts, created_at, finished_at FROM jobs ORDER BY created_at DESC LIMIT 100")).mappings().all()
        return {"items": [dict(row) for row in rows]}

@app.post("/v1/jobs", status_code=201)
def create_job(body: JobCreate, identity=Depends(principal)):
    with tenant_session(identity["tenant"]) as db:
        row = db.execute(text("INSERT INTO jobs(tenant_id, prompt, status, created_by) VALUES (:tenant, :prompt, 'queued', :actor) RETURNING id"), {"tenant": identity["tenant"], "prompt": body.prompt, "actor": identity["subject"]}).scalar_one()
        return {"id": row, "status": "queued"}

@app.get("/v1/jobs/{job_id}")
def get_job(job_id: UUID, identity=Depends(principal)):
    """RLS returns 404 for missing and other-tenant jobs alike."""
    with tenant_session(identity["tenant"]) as db:
        row = db.execute(text("""
            SELECT id, prompt, status, result, error, attempts, created_at, finished_at
            FROM jobs WHERE id=:id
        """), {"id": str(job_id)}).mappings().first()
        if row is None:
            raise HTTPException(404, "Job not found")
        return dict(row)

@app.post("/v1/rag/jobs", status_code=201)
def create_rag_job(body: RagJobCreate, identity=Depends(principal)):
    """Enqueue RAG retrieval for the authenticated tenant; never accept tenant from request."""
    configured_tenant = os.getenv("RAG_SERVICE_TENANT_ID", "")
    if not configured_tenant or configured_tenant != identity["tenant"]:
        raise HTTPException(403, "RAG is not configured for this tenant")
    if not os.getenv("RAG_SERVICE_URL") or not os.getenv("RAG_SERVICE_API_KEY"):
        raise HTTPException(503, "RAG service not configured")
    if body.reference_answer is not None and (
        not os.getenv("EVAL_SERVICE_URL") or not os.getenv("EVAL_SERVICE_API_KEY")
    ):
        raise HTTPException(503, "Evaluation service not configured")
    with tenant_session(identity["tenant"]) as db:
        job_id = db.execute(text("""
            INSERT INTO jobs(tenant_id, prompt, status, created_by, job_type, reference_answer)
            VALUES (:tenant, :question, 'queued', :actor, 'rag', :reference)
            RETURNING id
        """), {"tenant": identity["tenant"], "question": body.question,
               "actor": identity["subject"], "reference": body.reference_answer}).scalar_one()
        return {"id": job_id, "status": "queued", "job_type": "rag"}

# Import after principal is defined: the gateway reuses the same JWT authority.
from .document_gateway import router as knowledge_router
app.include_router(knowledge_router)


@app.post("/v1/agent/jobs", status_code=201)
def create_agent_job(body: AgentJobCreate, identity=Depends(principal)):
    """Tenant-bound durable agent job; only ATLAS worker calls the private agent."""
    if identity["tenant"] != os.getenv("AGENT_SERVICE_TENANT_ID", ""):
        raise HTTPException(403, "Agent service is not available for this tenant")
    if not os.getenv("AGENT_SERVICE_URL") or len(os.getenv("ATLAS_AGENT_SERVICE_KEY", "")) < 32:
        raise HTTPException(503, "Agent service not configured")
    with tenant_session(identity["tenant"]) as db:
        job_id = db.execute(text("""
            INSERT INTO jobs(tenant_id, prompt, status, created_by, job_type, agent_workflow)
            VALUES (:tenant, :question, 'queued', :actor, 'agent', :workflow)
            RETURNING id
        """), {"tenant": identity["tenant"], "question": body.question,
               "actor": identity["subject"], "workflow": body.workflow}).scalar_one()
        return {"id": job_id, "status": "queued", "job_type": "agent"}
)


class RagJobCreate(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    reference_answer: str | None = Field(default=None, min_length=1, max_length=16000)

def principal(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not SECRET or len(SECRET) < 32:
        raise HTTPException(503, "JWT secret not configured securely")
    try:
        claims = jwt.decode(credentials.credentials, SECRET, algorithms=["HS256"], issuer=ISSUER, audience=AUDIENCE, options={"require": ["sub", "tenant_id", "exp", "iss", "aud"]})
        tenant = str(UUID(claims["tenant_id"]))
        return {"subject": claims["sub"], "tenant": tenant}
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, "Invalid token")

@app.get("/health/live")
def live():
    return {"status": "ok"}

@app.get("/v1/jobs")
def list_jobs(identity=Depends(principal)):
    with tenant_session(identity["tenant"]) as db:
        rows = db.execute(text("SELECT id, prompt, status, result, error, attempts, created_at, finished_at FROM jobs ORDER BY created_at DESC LIMIT 100")).mappings().all()
        return {"items": [dict(row) for row in rows]}

@app.post("/v1/jobs", status_code=201)
def create_job(body: JobCreate, identity=Depends(principal)):
    with tenant_session(identity["tenant"]) as db:
        row = db.execute(text("INSERT INTO jobs(tenant_id, prompt, status, created_by) VALUES (:tenant, :prompt, 'queued', :actor) RETURNING id"), {"tenant": identity["tenant"], "prompt": body.prompt, "actor": identity["subject"]}).scalar_one()
        return {"id": row, "status": "queued"}

@app.get("/v1/jobs/{job_id}")
def get_job(job_id: UUID, identity=Depends(principal)):
    """RLS returns 404 for missing and other-tenant jobs alike."""
    with tenant_session(identity["tenant"]) as db:
        row = db.execute(text("""
            SELECT id, prompt, status, result, error, attempts, created_at, finished_at
            FROM jobs WHERE id=:id
        """), {"id": str(job_id)}).mappings().first()
        if row is None:
            raise HTTPException(404, "Job not found")
        return dict(row)

@app.post("/v1/rag/jobs", status_code=201)
def create_rag_job(body: RagJobCreate, identity=Depends(principal)):
    """Enqueue RAG retrieval for the authenticated tenant; never accept tenant from request."""
    configured_tenant = os.getenv("RAG_SERVICE_TENANT_ID", "")
    if not configured_tenant or configured_tenant != identity["tenant"]:
        raise HTTPException(403, "RAG is not configured for this tenant")
    if not os.getenv("RAG_SERVICE_URL") or not os.getenv("RAG_SERVICE_API_KEY"):
        raise HTTPException(503, "RAG service not configured")
    if body.reference_answer is not None and (
        not os.getenv("EVAL_SERVICE_URL") or not os.getenv("EVAL_SERVICE_API_KEY")
    ):
        raise HTTPException(503, "Evaluation service not configured")
    with tenant_session(identity["tenant"]) as db:
        job_id = db.execute(text("""
            INSERT INTO jobs(tenant_id, prompt, status, created_by, job_type, reference_answer)
            VALUES (:tenant, :question, 'queued', :actor, 'rag', :reference)
            RETURNING id
        """), {"tenant": identity["tenant"], "question": body.question,
               "actor": identity["subject"], "reference": body.reference_answer}).scalar_one()
        return {"id": job_id, "status": "queued", "job_type": "rag"}

# Import after principal is defined: the gateway reuses the same JWT authority.
from .document_gateway import router as knowledge_router
app.include_router(knowledge_router)


@app.post("/v1/agent/jobs", status_code=201)
def create_agent_job(body: AgentJobCreate, identity=Depends(principal)):
    """Tenant-bound durable agent job; only ATLAS worker calls the private agent."""
    if identity["tenant"] != os.getenv("AGENT_SERVICE_TENANT_ID", ""):
        raise HTTPException(403, "Agent service is not available for this tenant")
    if not os.getenv("AGENT_SERVICE_URL") or len(os.getenv("ATLAS_AGENT_SERVICE_KEY", "")) < 32:
        raise HTTPException(503, "Agent service not configured")
    with tenant_session(identity["tenant"]) as db:
        job_id = db.execute(text("""
            INSERT INTO jobs(tenant_id, prompt, status, created_by, job_type)
            VALUES (:tenant, :question, 'queued', :actor, 'agent')
            RETURNING id
        """), {"tenant": identity["tenant"], "question": body.question,
               "actor": identity["subject"]}).scalar_one()
        return {"id": job_id, "status": "queued", "job_type": "agent"}
