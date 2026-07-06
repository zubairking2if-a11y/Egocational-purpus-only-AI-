from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from runners.drivers.nmap import run_nmap_simulated

router = APIRouter()

class ScanRequest(BaseModel):
    target: str
    tool: str = "nmap"

@router.post("/scan")
async def run_scan(req: ScanRequest, background_tasks: BackgroundTasks):
    # Enqueue a background simulated run
    background_tasks.add_task(run_nmap_simulated, req.target)
    return {"status": "enqueued", "target": req.target}
