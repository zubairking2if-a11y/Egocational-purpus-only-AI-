"""Executor that runs commands either simulated or (optionally) live via subprocess or Docker sandbox.

All live execution is gated on configuration (enable_live_execution) and an allowlist
of permitted tools/flags to minimize risk. By default the scaffold uses simulated runs.
"""
import asyncio
import subprocess
from typing import List, Dict, Any

from pathlib import Path

from core.exceptions import RunnerError

# Local import to avoid circular imports at module import time

def is_live_enabled(config: Dict[str, Any]) -> bool:
    return bool(config.get("security", {}).get("enable_live_execution", False))

async def run_command_simulated(cmd: List[str], timeout: int = 300) -> Dict[str, Any]:
    await asyncio.sleep(0.1)
    return {"returncode": 0, "stdout": "[simulated output]", "stderr": ""}

async def run_command_local(cmd: List[str], timeout: int = 300) -> Dict[str, Any]:
    """Run a command on the local host using subprocess (use with extreme caution).

    This function is NOT used unless configuration explicitly enables local execution.
    """
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise RunnerError("Process timed out")
        return {"returncode": proc.returncode, "stdout": (stdout or b"").decode(errors="ignore"), "stderr": (stderr or b"").decode(errors="ignore")} 
    except Exception as e:
        raise RunnerError(str(e))

async def run_command_docker(cmd: List[str], image: str = "alpine:latest", volumes: Dict[str, Dict[str, str]] = None, timeout: int = 300) -> Dict[str, Any]:
    try:
        from runners.sandbox import run_in_docker
    except Exception as e:
        raise RunnerError("Docker sandbox not available: {}".format(e))

    return run_in_docker(image, cmd, volumes=volumes, timeout=timeout)
