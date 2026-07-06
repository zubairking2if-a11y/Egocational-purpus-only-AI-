"""Driver stubs for other tools."""
async def run_nuclei_simulated(target: str):
    return {"target": target, "findings": []}

async def run_ffuf_simulated(target: str):
    return {"target": target, "results": []}
