"""Lightweight in-process async Pub/Sub EventBus used by the app."""
import asyncio
from typing import Callable, Dict, List, Any

class EventBus:
    def __init__(self):
        self._subs: Dict[str, List[Callable[[Any], None]]] = {}

    def subscribe(self, event_name: str, callback: Callable[[Any], None]):
        self._subs.setdefault(event_name, []).append(callback)

    async def publish(self, event_name: str, payload: Any):
        for cb in self._subs.get(event_name, []):
            # schedule callbacks but do not await to keep bus fast
            asyncio.create_task(cb(payload))
