"""Reconnaissance agent stub that emits requests to run network scans."""
from core.events import EventBus

class ReconnaissanceAgent:
    def __init__(self, bus: EventBus):
        self.bus = bus

    async def run_target(self, target: str):
        # request a scan via an event; listeners (runners/worker) will pick this up
        await self.bus.publish("RunScanRequest", {"target": target, "tool": "nmap"})
