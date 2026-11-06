"""Runnable inference API. In-memory jobs are intentionally single-process only."""
import hmac
import os
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field
from .advanced import Scheduler

class SubmitRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)

class JobResponse(BaseModel):
    id: str
    status: str
    result: str | None = None
    error: str | None = None
    attempts: int

async def demo_inference(prompt: str) -> str:
    """Deterministic provider; replace with a real LLM adapter."""
    return prompt.upper()

def create_app(*, key: str | None = None, infer=None, capacity: int = 64, workers: int = 2) -> FastAPI:
    secret = key if key is not None else os.getenv("INFERENCE_API_KEY", "")
    if not secret:
        raise RuntimeError("INFERENCE_API_KEY must be set")
    scheduler = Scheduler(infer or demo_inference, workers=workers, capacity=capacity)
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await scheduler.start()
        try:
            yield
        finally:
            await scheduler.close()
    app = FastAPI(title="Inference Platform", version="0.3.0", lifespan=lifespan)
    app.state.scheduler = scheduler
    def authorize(x_api_key: str | None = Header(default=None)):
        if not x_api_key or not hmac.compare_digest(x_api_key, secret):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    @app.get("/health/live")
    async def liveness():
        return {"status": "ok"}
    @app.get("/health/ready")
    async def readiness(_: None = Depends(authorize)):
        return {"status": "ok", "workers": len(scheduler._running)}
    @app.post("/v1/jobs", response_model=JobResponse, status_code=202)
    async def submit(body: SubmitRequest, _: None = Depends(authorize)):
        try:
            job = scheduler.submit(body.prompt)
        except OverflowError:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Queue full", headers={"Retry-After": "1"})
        return JobResponse(id=job.id, status=job.status, attempts=job.attempts)
    @app.get("/v1/jobs/{job_id}", response_model=JobResponse)
    async def get_job(job_id: str, _: None = Depends(authorize)):
        job = scheduler.tasks.get(job_id)
        if job is None:
            raise HTTPException(404, "Unknown job")
        return JobResponse(id=job.id, status=job.status, result=job.result, error=job.error, attempts=job.attempts)
    @app.get("/v1/metrics")
    async def metrics(_: None = Depends(authorize)):
        statuses = {state: 0 for state in ("queued", "running", "completed", "failed")}
        for job in scheduler.tasks.values():
            statuses[job.status] += 1
        return {"queue_depth": scheduler.queue.qsize(), "jobs": statuses}
    return app
