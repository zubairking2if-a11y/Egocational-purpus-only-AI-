"""Analyzers pipeline coordinating structural and cognitive checks."""
from analyzers.structural import headers

async def analyze_scan(scan_result: dict) -> dict:
    # run quick structural checks
    hdrs = headers.check_headers(scan_result)
    return {"headers": hdrs}
