import asyncio
from dataclasses import dataclass
from uuid import uuid4
from typing import Awaitable, Callable

@dataclass
class Job:
    id: str
    prompt: str
    status: str = "queued"
    result: str | None = None
    error: str | None = None

class InferenceService:
    def __init__(self, handler: Callable[[str], Awaitable[str]], concurrency: int = 2, capacity: int = 100):
        if concurrency < 1 or capacity < 1:
            raise ValueError("Positive concurrency and capacity required")
        self.handler = handler
        self.jobs: dict[str, Job] = {}
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=capacity)
        self.concurrency = concurrency
        self.workers: list[asyncio.Task] = []

    async def start(self):
        if not self.workers:
            self.workers = [asyncio.create_task(self._worker()) for _ in range(self.concurrency)]

    async def stop(self):
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers = []

    def submit(self, prompt: str) -> Job:
        if self.queue.full():
            raise OverflowError("Inference queue at capacity")
        job = Job(id=str(uuid4()), prompt=prompt)
        self.jobs[job.id] = job
        self.queue.put_nowait(job.id)
        return job

    async def _worker(self):
        while True:
            job_id = await self.queue.get()
            job = self.jobs[job_id]
            job.status = "running"
            try:
                job.result = await self.handler(job.prompt)
                job.status = "completed"
            except Exception as exc:
                job.error = str(exc)
                job.status = "failed"
            finally:
                self.queue.task_done()

async def demo_handler(prompt: str) -> str:
    await asyncio.sleep(0.01)
    return prompt.upper()
