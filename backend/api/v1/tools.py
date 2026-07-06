"""Tools API — now enqueues actual background tasks to the Broker and returns a job id.

By default the tasks will use the simulation mode unless you enable live execution in
config/security.yaml and config/tools.yaml. Do not enable live execution until you've
implemented sandboxing and reviewed allowlists.
"""
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from worker.broker import Broker
import yaml

router = APIRouter()

class ScanRequest(BaseModel):
    target: str
    tool: str = "nmap"

@router.post("/scan")
async def run_scan(req: ScanRequest):
    # Enqueue a background simulated run using the Broker singleton (imported by server)
    from worker.broker import Broker
    from runners.drivers.nmap import run_nmap

    with open("config/tools.yaml", "r") as fh:
        cfg = yaml.safe_load(fh)

    async def task():
        try:
            res = await run_nmap(req.target, cfg.get("nmap", {}).get("default_args", "-sV -oX -").split(), {"tools": cfg})
            print("Scan completed:", res)
        except Exception as e:
            print("Scan error:", e)

    broker = Broker()
    await broker.enqueue(task)
    return {"status": "enqueued", "target": req.target}
