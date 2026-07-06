import asyncio
import json
import uuid
import time

import pytest
import httpx
import websockets

# --- Configuration (edit these to match your backend) ---
BASE_HTTP = "http://localhost:8000"   # where your backend is reachable
SCAN_ENDPOINT = f"{BASE_HTTP}/api/v1/scan"   # HTTP endpoint to request a scan (POST)
WS_URI_TEMPLATE = "ws://localhost:8000/ws/sessions/{session_id}/logs"
JWT_TOKEN = None  # "Bearer eyJ..." or None
# ------------------------------------------------------

REQUEST_TIMEOUT = 60  # seconds to wait for logs before failing the test
WS_WAIT_TIMEOUT = 5   # seconds for polling recv before checking stop condition

@pytest.mark.asyncio
async def test_sandboxed_scan_streams_logs():
    """
    End-to-end test:
    1. POST a scan request with a unique session_id
    2. Connect to the session websocket and collect logs
    3. Ensure at least some logs were received and the scan finished (or timed out)
    """
    session_id = str(uuid.uuid4())
    ws_uri = WS_URI_TEMPLATE.format(session_id=session_id)

    http_headers = {"Content-Type": "application/json"}
    ws_headers = {}
    if JWT_TOKEN:
        http_headers["Authorization"] = JWT_TOKEN
        ws_headers["Authorization"] = JWT_TOKEN

    received_messages = []
    stop_event = asyncio.Event()

    async def ws_listener():
        try:
            async with websockets.connect(ws_uri, extra_headers=ws_headers) as ws:
                while not stop_event.is_set():
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=WS_WAIT_TIMEOUT)
                        received_messages.append(msg)
                        lower = (msg or "").lower()
                        if "exit code" in lower or "completed" in lower or "finished" in lower:
                            stop_event.set()
                            break
                    except asyncio.TimeoutError:
                        continue
        except Exception as e:
            received_messages.append(f"__ws_exception__:{e}")
            stop_event.set()

    ws_task = asyncio.create_task(ws_listener())

    await asyncio.sleep(0.2)

    payload = {
        "session_id": session_id,
        "command": "echo hello-from-sandbox && sleep 1 && echo finished"
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(SCAN_ENDPOINT, headers=http_headers, json=payload)
    assert resp.status_code in (200, 202), f"scan endpoint error: {resp.status_code} {resp.text}"

    start = time.monotonic()
    while not stop_event.is_set() and (time.monotonic() - start) < REQUEST_TIMEOUT:
        await asyncio.sleep(0.2)

    stop_event.set()
    await asyncio.wait_for(ws_task, timeout=5.0)

    assert len(received_messages) > 0, f"No logs received for session {session_id}. Raw: {received_messages}"

    combined = "\n".join(received_messages)
    assert "hello-from-sandbox" in combined or "finished" in combined.lower() or "exit code" in combined.lower()
