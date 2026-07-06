"""Websocket connection broker placeholder."""
from typing import Dict

clients: Dict[str, object] = {}

async def register(client_id: str, ws):
    clients[client_id] = ws

async def unregister(client_id: str):
    clients.pop(client_id, None)
