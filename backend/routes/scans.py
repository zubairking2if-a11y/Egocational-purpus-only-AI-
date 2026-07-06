"""API routes for scan operations."""

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
import logging

from backend.runner.executor import run_pentest_tool

logger = logging.getLogger("offline-pentest.routes.scans")

router = APIRouter(prefix="/api/v1", tags=["scans"])


class ScanStartRequest(BaseModel):
    """Request body for initiating a new scan job."""
    session_id: str
    command: str


class ScanResponse(BaseModel):
    """Response body for scan operations."""
    status: str
    session_id: str
    message: str = None


@router.post("/scan/start", response_model=ScanResponse)
async def start_scan_job(
    request: ScanStartRequest,
    background_tasks: BackgroundTasks
) -> ScanResponse:
    """Start a new pentesting tool execution as a background task.
    
    This endpoint:
    1. Accepts a session ID and command string
    2. Validates the command (handled in executor)
    3. Spawns the subprocess in the background
    4. Returns 202 Accepted immediately (doesn't block)
    5. Output streams live to WebSocket at /api/v1/ws/terminal/{session_id}
    
    Args:
        request: ScanStartRequest with session_id and command
        background_tasks: FastAPI BackgroundTasks for async execution
    
    Returns:
        ScanResponse with status and session_id
    
    Example:
        POST /api/v1/scan/start
        {
            "session_id": "sess-123",
            "command": "nmap -sV -p 22,80 example.com"
        }
        
        Response (202):
        {
            "status": "accepted",
            "session_id": "sess-123",
            "message": "Scan job dispatched. Connect to /api/v1/ws/terminal/sess-123?token=<JWT> to stream output."
        }
    """
    logger.info(f"Scan start request for session {request.session_id}: {request.command}")
    
    # Add the runner task to background execution queue
    background_tasks.add_task(run_pentest_tool, request.session_id, request.command)
    
    return ScanResponse(
        status="accepted",
        session_id=request.session_id,
        message=f"Scan job dispatched. Connect to WebSocket at /api/v1/ws/terminal/{request.session_id}?token=<JWT> to stream output."
    )
