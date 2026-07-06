"""Background tasks (placeholders)"""
async def scan_task(target: str, tool: str = "nmap"):
    # In production, this would call runners/executor and persist results
    return {"target": target, "status": "simulated"}
