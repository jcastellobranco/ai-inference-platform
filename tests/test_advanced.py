import asyncio
from inference_platform.advanced import Scheduler
def test_scheduler():
    async def go():
        async def infer(text): return text.upper()
        scheduler=Scheduler(infer,workers=1,capacity=2)
        await scheduler.start()
        task=scheduler.submit("hello")
        await scheduler.close()
        assert task.status=="completed"
        assert task.result=="HELLO"
    asyncio.run(go())
