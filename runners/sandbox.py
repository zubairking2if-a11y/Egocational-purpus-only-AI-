"""Sandbox manager that can run tools inside a Docker container when enabled.

This is intended as a safer execution path than executing tools in the host
process. It still requires careful configuration (read the README and set
config/tools.yaml -> live_execution to true only after you review security).
"""
from typing import List, Dict, Optional
import subprocess
import shlex
import os

try:
    import docker
except Exception:
    docker = None


def run_in_docker(image: str, cmd: List[str], volumes: Optional[Dict[str, Dict[str, str]]] = None, timeout: int = 300) -> Dict[str, str]:
    """Run a command inside a short-lived Docker container and return stdout/stderr/rc.

    volumes example: {"/host/path": {"bind":"/container/path","mode":"ro"}}
    """
    if docker is None:
        raise RuntimeError("docker SDK not available; install docker Python package to enable live sandboxing")

    client = docker.from_env()
    # Ensure image is available; this pulls if missing which may be undesirable in air-gapped setups
    try:
        client.images.pull(image)
    except Exception:
        # If pull fails (e.g., air-gapped), assume image is already present locally
        pass

    cmd_str = " ".join(shlex.quote(c) for c in cmd)
    container = None
    try:
        container = client.containers.run(
            image,
            command=cmd_str,
            detach=True,
            network_disabled=True,
            volumes=volumes or {},
            cpu_shares=512,
            mem_limit="512m",
            stderr=True,
            stdout=True,
            remove=True
        )
        result = container.logs(stdout=True, stderr=True, stream=False, timestamps=False)
        # container.wait() returns dict with StatusCode
        exit_info = container.wait(timeout=timeout)
        rc = exit_info.get("StatusCode", 0)
        stdout = container.logs(stdout=True, stderr=False).decode(errors="ignore")
        stderr = container.logs(stdout=False, stderr=True).decode(errors="ignore")
        return {"returncode": rc, "stdout": stdout, "stderr": stderr}
    except Exception as e:
        # Best-effort: if something goes wrong, surface the error message but do not execute on host
        return {"returncode": 1, "stdout": "", "stderr": str(e)}
    finally:
        try:
            if container:
                container.remove(force=True)
        except Exception:
            pass
