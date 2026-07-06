"""
Async-friendly Docker SDK executor for running pentest tools in isolated containers.

Behavior:
- Runs the Docker APIClient calls synchronously inside a threadpool (run_in_executor).
- Attaches to container stdout/stderr and forwards chunks to ActiveSessionManager.broadcast_to_session.
- Enforces a global timeout from SANDBOX_MAX_EXEC_TIME; on timeout attempts to kill the container.
- Cleans up the container on exit.
"""
import asyncio
import logging
import os
import shlex
from typing import List

import docker
from docker.errors import APIError

from backend.websocket.terminal_processor import ActiveSessionManager

logger = logging.getLogger("offline-pentest.runner.docker_sdk_executor")

MAX_EXECUTION_TIME = int(os.getenv("SANDBOX_MAX_EXEC_TIME", "300"))
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "kali-linux-headless:latest")


def _execute_container_sync(session_id: str, command_list: List[str], loop: asyncio.AbstractEventLoop) -> int:
    """
    Synchronous worker that uses docker.APIClient to create/start/attach to a container,
    streaming output back into the provided asyncio loop via run_coroutine_threadsafe.
    Returns the container's exit code on normal termination.
    """
    client = docker.APIClient(base_url="unix://var/run/docker.sock")
    container_name = f"sandbox-{session_id}"

    try:
        host_config = client.create_host_config(
            cap_drop=["ALL"],
            mem_limit="512m",
            nano_cpus=1000000000,  # 1 CPU
            network_mode="pentest-sandbox-net",
            auto_remove=False,  # we remove explicitly in finally to ensure inspect is available
        )

        container = client.create_container(
            image=SANDBOX_IMAGE,
            command=command_list,
            name=container_name,
            host_config=host_config,
            environment={"TERM": "xterm-256color"},
        )
        container_id = container.get("Id")
        logger.info(f"Created container {container_name} (ID: {container_id[:12]})")

        # Attach stream before starting to avoid racing for early output
        log_stream = client.attach(container=container_id, stream=True, stdout=True, stderr=True, demux=False)

        client.start(container=container_id)

        # Stream chunks and forward to the async loop
        for chunk in log_stream:
            if not chunk:
                continue
            try:
                text_frame = chunk.decode("utf-8", errors="surrogateescape")
            except Exception:
                # Fallback: ensure we always forward something readable
                text_frame = repr(chunk)

            # Schedule the broadcast on the main loop
            asyncio.run_coroutine_threadsafe(
                ActiveSessionManager.broadcast_to_session(session_id, text_frame),
                loop,
            )

        # Inspect container to get exit code
        inspect_data = client.inspect_container(container=container_id)
        exit_code = inspect_data.get("State", {}).get("ExitCode", 0)
        logger.info(f"Container {container_name} exited with code {exit_code}")
        return exit_code

    except APIError as ae:
        logger.exception("Docker API error during container lifecycle")
        raise ae
    except Exception:
        logger.exception("Unexpected error running container runtime")
        raise
    finally:
        # Ensure container removal; tolerate any errors during cleanup
        try:
            client.remove_container(container=container_name, force=True)
            logger.debug(f"Removed container {container_name} during cleanup")
        except Exception:
            logger.debug(f"Could not remove container {container_name}; it may already be gone")


async def run_sandboxed_container_tool(session_id: str, raw_command: str) -> int:
    """
    Async entrypoint. Splits the raw_command, dispatches the sync worker into an executor,
    awaits it with a timeout, and handles timeout-driven container termination.
    """
    command_list = shlex.split(raw_command)
    loop = asyncio.get_running_loop()

    logger.info(f"Dispatching Docker SDK executor for session {session_id}: {command_list}")

    # Run sync container lifecycle in executor (thread pool)
    exec_future = loop.run_in_executor(None, _execute_container_sync, session_id, command_list, loop)

    try:
        exit_code = await asyncio.wait_for(exec_future, timeout=MAX_EXECUTION_TIME)
        # final status message
        await ActiveSessionManager.broadcast_to_session(
            session_id,
            f"\r\n\x1b[1;32m[+] Execution complete. Process exited with status code: {exit_code}\x1b[0m\r\n",
        )
        return exit_code

    except asyncio.TimeoutError:
        logger.error(f"Sandbox runtime exceeded {MAX_EXECUTION_TIME}s for session {session_id}")
        # Best-effort container kill/cleanup in background
        def _kill_and_remove(sid: str):
            try:
                c = docker.APIClient(base_url="unix://var/run/docker.sock")
                name = f"sandbox-{sid}"
                try:
                    c.kill(container=name)
                except Exception:
                    pass
                try:
                    c.remove_container(container=name, force=True)
                except Exception:
                    pass
            except Exception:
                logger.exception("Failed to kill/remove timed-out container")

        # Schedule synchronous kill in executor (do not await it here to avoid further blocking)
        loop.run_in_executor(None, _kill_and_remove, session_id)

        await ActiveSessionManager.broadcast_to_session(
            session_id,
            f"\r\n\x1b[1;31m[!] Security Policy Enforcement: Execution timeout exceeded ({MAX_EXECUTION_TIME}s).\x1b[0m\r\n",
        )
        raise TimeoutError("Container sandbox execution timeout exceeded.")
