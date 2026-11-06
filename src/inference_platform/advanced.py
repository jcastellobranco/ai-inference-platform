"""Async inference scheduler with retries, timeouts, queue backpressure and shutdown."""
import asyncio
from dataclasses import dataclass, field
from time import monotonic
from uuid import uuid4
from typing import Awaitable, Callable

@dataclass
class Task:
    id: str
    payload: str
    status: str = "queued"
    result: str | None = None
    error: str | None = None
    attempts: int = 0
    created_at: float = field(default_factory=monotonic)

class Scheduler:
    def __init__(self, infer: Callable[[str], Awaitable[str]], workers: int = 2, capacity: int = 64, timeout: float = 30, retries: int = 1):
        if workers < 1 or capacity < 1 or timeout <= 0 or retries < 0:
            raise ValueError("Invalid scheduler configuration")
        self.infer, self.workers, self.timeout, self.retries = infer, workers, timeout, retries
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=capacity)
        self.tasks: dict[str, Task] = {}
        self._running: list[asyncio.Task] = []

    async def start(self):
        if not self._running:
            self._running = [asyncio.create_task(self._worker()) for _ in range(self.workers)]

    async def close(self):
        await self.queue.join()
        for worker in self._running:
            worker.cancel()
        await asyncio.gather(*self._running, return_exceptions=True)
        self._running.clear()

    def submit(self, payload: str) -> Task:
        if self.queue.full():
            raise OverflowError("Queue capacity exceeded")
        task = Task(id=str(uuid4()), payload=payload)
        self.tasks[task.id] = task
        self.queue.put_nowait(task.id)
        return task

    async def _worker(self):
        while True:
            task = self.tasks[await self.queue.get()]
            try:
                task.status = "running"
                for attempt in range(self.retries+1):
                    task.attempts += 1
                    try:
                        task.result = await asyncio.wait_for(self.infer(task.payload), timeout=self.timeout)
                        task.status = "completed"
                        break
                    except Exception as exc:
                        task.error = f"{type(exc).__name__}: {exc}"
                        if attempt == self.retries:
                            task.status = "failed"
                        else:
                            await asyncio.sleep(min(0.1*2**attempt, 1))
            finally:
                self.queue.task_done()
