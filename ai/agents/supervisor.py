"""Agent supervisor coordinates multiple agents via EventBus."""
from core.events import EventBus

class Supervisor:
    def __init__(self, event_bus: EventBus):
        self.bus = event_bus

    async def start(self):
        # subscribe to important events
        self.bus.subscribe("ToolFinishedEvent", self.on_tool_finished)

    async def on_tool_finished(self, payload):
        # basic reaction example
        print("Supervisor received ToolFinishedEvent:", payload)
