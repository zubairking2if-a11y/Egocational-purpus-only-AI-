"""Core application lifecycle and simple bootstrap."""
from .events import EventBus

class Application:
    def __init__(self):
        self.events = EventBus()
        self.started = False

    async def start(self):
        self.started = True
        # further startup tasks (load config, connect DB, start workers)

    async def stop(self):
        self.started = False
