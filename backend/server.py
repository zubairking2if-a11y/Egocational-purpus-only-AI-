"""Backend server: start background worker broker on startup so scan requests are processed.

This module wires the in-memory Broker and exposes endpoints. By default all runs remain simulated.
"""
from fastapi import FastAPI
from pydantic import BaseModel
import os
import asyncio

from worker.broker import Broker
from core.events import EventBus

app = FastAPI(title="Offline Pentest AI (scaffold)")

broker = Broker()

@app.on_event("startup")
async def startup_event():
    # start worker loop in background
    asyncio.create_task(broker.worker_loop())

@app.get("/health")
async def health():
    return {"status":"ok"}

class ScanRequest(BaseModel):
    target: str
    tool: str = "nmap"

@app.post("/api/v1/scan")
async def scan(req: ScanRequest):
    # enqueue the task to the broker; worker will run it
    async def task():
        from runners.drivers.nmap import run_nmap
        from configparser import ConfigParser
        # Load YAML config using a simple safe loader to avoid extra deps
        import yaml
        with open("config/tools.yaml", "r") as fh:
            cfg = yaml.safe_load(fh)
        try:
            result = await run_nmap(req.target, cfg.get("nmap", {}).get("default_args", "-sV -oX -").split(), {"tools": cfg})
            # In a full implementation we'd persist result to DB and emit events
            print("Scan result:", result)
        except Exception as e:
            print("Scan failed:", e)

    await broker.enqueue(task)
    return {"status": "enqueued", "target": req.target}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.server:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
