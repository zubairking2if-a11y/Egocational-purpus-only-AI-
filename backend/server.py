from fastapi import FastAPI
from pydantic import BaseModel
import os

app = FastAPI(title="Offline Pentest AI (scaffold)")

@app.get("/health")
async def health():
    return {"status":"ok"}

class ScanRequest(BaseModel):
    target: str
    tool: str = "nmap"

@app.post("/api/v1/scan")
async def scan(req: ScanRequest):
    # placeholder: do not execute tools in scaffold
    return {
        "target": req.target,
        "tool": req.tool,
        "status": "simulated",
        "note": "This is a safe scaffold. Replace with a secure runner implementation before running real scans."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.server:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
