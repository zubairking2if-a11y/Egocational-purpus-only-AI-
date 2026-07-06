"""Backend server: start background worker broker on startup so scan requests are processed.

This module wires the in-memory Broker, WebSocket routes, and exposes endpoints.
By default all runs execute in isolated Docker containers for security.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import asyncio
import logging

from worker.broker import Broker
from core.events import EventBus
from backend.routes.terminal import router as terminal_router
from backend.routes.scans import router as scans_router
from backend.startup import run_startup_checks

logger = logging.getLogger("offline-pentest.backend.server")

app = FastAPI(title="Offline Pentest AI (scaffold)")

# Configure CORS for local development and xterm.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

broker = Broker()


@app.on_event("startup")
async def startup_event():
    """Run startup checks and start background worker loop."""
    logger.info("Backend application starting...")
    
    # Verify Docker and sandbox infrastructure
    checks_passed = await run_startup_checks()
    if not checks_passed:
        logger.warning("Startup checks failed. Docker sandbox execution may not be available.")
    
    # Start worker loop in background
    logger.info("Starting background worker broker...")
    asyncio.create_task(broker.worker_loop())


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


class ScanRequest(BaseModel):
    target: str
    tool: str = "nmap"


@app.post("/api/v1/scan")
async def scan(req: ScanRequest):
    """Enqueue a scan task to the background broker.
    
    Args:
        req: ScanRequest with target and tool name
    
    Returns:
        Status dict with enqueue confirmation
    """
    # Define the scan task
    async def task():
        try:
            from runners.drivers.nmap import run_nmap
            from configparser import ConfigParser
            import yaml
            
            with open("config/tools.yaml", "r") as fh:
                cfg = yaml.safe_load(fh)
            
            result = await run_nmap(
                req.target,
                cfg.get("nmap", {}).get("default_args", "-sV -oX -").split(),
                {"tools": cfg}
            )
            logger.info(f"Scan completed for {req.target}: {result}")
        except Exception as e:
            logger.error(f"Scan failed for {req.target}: {e}")
    
    # Enqueue to broker
    await broker.enqueue(task)
    return {"status": "enqueued", "target": req.target}


# Register routers
app.include_router(terminal_router)
app.include_router(scans_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True
    )
