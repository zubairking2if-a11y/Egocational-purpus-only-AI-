"""Worker broker (very simple in-memory queue for scaffold)."""
import asyncio

class Broker:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def enqueue(self, task):
        await self.queue.put(task)

    async def worker_loop(self):
        while True:
            task = await self.queue.get()
            try:
                await task()
            except Exception:
                pass
            self.queue.task_done()
