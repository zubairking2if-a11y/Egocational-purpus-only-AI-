"""Nmap driver that supports simulated mode and a gated live mode.

When config.tools.live_execution is false this driver returns simulated results.
If live_execution is true and the runtime environment allows, it will execute nmap
with a strict subset of flags (see config/tools.yaml -> allowed_flags) and parse
basic XML output to generate structured results.
"""
import asyncio
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

from core.exceptions import RunnerError
from runners import executor

async def run_nmap(target: str, args: List[str], config: Dict[str, Any]) -> Dict[str, Any]:
    live = bool(config.get("tools", {}).get("live_execution", False))
    if not live:
        # Return realistic simulated output
        return {
            "target": target,
            "ports": [
                {"port": 22, "service": "ssh", "state": "open"},
                {"port": 80, "service": "http", "state": "open"}
            ],
            "raw": "<nmap>simulated</nmap>"
        }

    # Validate args against allowlist
    allowed_flags = set(config.get("tools", {}).get("nmap", {}).get("allowed_flags", []))
    for a in args:
        # simple check: ensure flags start with '-' or are numeric/passed as port specs
        if a.startswith("-") and not any(a.startswith(f) for f in allowed_flags):
            raise RunnerError(f"Flag {a} not allowed by configuration")

    cmd = [config.get("tools", {}).get("nmap", {}).get("binary", "nmap")] + args + [target]
    res = await executor.run_command_local(cmd)
    if res.get("returncode", 1) != 0:
        raise RunnerError("nmap failed: " + (res.get("stderr") or ""))

    stdout = res.get("stdout", "")
    # Try to parse XML
    try:
        root = ET.fromstring(stdout)
        ports = []
        for host in root.findall("host"):
            for port in host.findall("ports/port"):
                pnum = int(port.get("portid", "0"))
                state = port.find("state").get("state") if port.find("state") is not None else "unknown"
                service = port.find("service").get("name") if port.find("service") is not None else "unknown"
                ports.append({"port": pnum, "service": service, "state": state})
        return {"target": target, "ports": ports, "raw": stdout}
    except ET.ParseError:
        # If parsing fails, return raw output for offline inspection
        return {"target": target, "ports": [], "raw": stdout}
