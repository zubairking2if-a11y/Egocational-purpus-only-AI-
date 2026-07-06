"""Docker-based sandboxed executor for isolated pentesting tool execution.

This module provides:
- Isolated container spawning via Docker SDK
- Real-time output streaming from container logs
- Resource limits (memory, CPU)
- Capability dropping for security
- Automatic cleanup on completion or timeout
"""

import asyncio
import os
import shlex
import logging
from typing import Optional

from backend.websocket.terminal_processor import stream_process_output_to_broker

logger = logging.getLogger("offline-pentest.runner.docker_executor")

# Configuration limits for sandbox execution
MAX_EXECUTION_TIME = int(os.getenv("SANDBOX_MAX_EXEC_TIME", "300"))

# Docker image with pentesting utilities pre-loaded
# For production, use a hardened, minimal image
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "kali-linux-headless:latest")

# Docker network for isolated sandbox communication
SANDBOX_NETWORK = os.getenv("SANDBOX_NETWORK", "pentest-sandbox-net")

logger.info(f"Docker executor configured: image={SANDBOX_IMAGE}, network={SANDBOX_NETWORK}, timeout={MAX_EXECUTION_TIME}s")


async def run_sandboxed_container_tool(session_id: str, raw_command: str) -> int:
    """Spawn an isolated Docker container to execute a pentesting tool.
    
    This function:
    1. Parses and validates the command
    2. Constructs a Docker run command with security constraints
    3. Spawns the container (automatically cleaned up with --rm)
    4. Streams container stdout/stderr to the WebSocket broker
    5. Enforces timeout and cleanup on completion or failure
    
    Security features:
    - Container runs in isolated bridge network (optionally with no internet)
    - All Linux capabilities dropped (--cap-drop ALL)
    - Memory limited to 512MB
    - CPU limited to 1.0 core
    - No host filesystem access by default
    - Automatic container cleanup (--rm)
    
    Args:
        session_id: Unique session identifier for output routing
        raw_command: Raw command string to execute in container
    
    Returns:
        Container exit code (0 = success, non-zero = failure)
    
    Raises:
        Exception: If container spawn or streaming fails
    
    Example:
        exit_code = await run_sandboxed_container_tool(
            "sess-123",
            "nmap -sV -p 22,80 example.com"
        )
    """
    # Parse command arguments
    try:
        command_list = shlex.split(raw_command)
    except ValueError as e:
        logger.error(f"Command parse failure for session {session_id}: {str(e)}")
        raise ValueError(f"Invalid command syntax: {str(e)}")
    
    if not command_list:
        raise ValueError("Empty command list")
    
    logger.info(f"Spawning Docker sandbox for session {session_id}: {command_list[0]}")
    logger.debug(f"Full command: {' '.join(command_list)}")
    
    # Construct Docker CLI command with security constraints
    # The --rm flag ensures the container is deleted after completion
    docker_command = [
        "docker", "run", "--rm",
        "--name", f"sandbox-{session_id}",
        "--network", SANDBOX_NETWORK,          # Isolated bridge network
        "--cap-drop", "ALL",                   # Drop all Linux capabilities
        "--memory", "512m",                    # Memory limit
        "--cpus", "1.0",                       # CPU core limit
        "--read-only",                         # Read-only root filesystem
        "-e", "TERM=xterm-256color",           # Terminal emulation
        "-e", f"SESSION_ID={session_id}",     # Pass session ID to container
        SANDBOX_IMAGE
    ] + command_list
    
    logger.debug(f"Docker command: {' '.join(docker_command)}")
    
    process = None
    try:
        # Spawn Docker process
        process = await asyncio.create_subprocess_exec(
            *docker_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # Merge stderr into stdout
            env={"PATH": os.getenv("PATH", "/usr/bin:/bin")}
        )
        
        logger.debug(f"Docker process spawned with PID {process.pid} for session {session_id}")
        
        if not process.stdout:
            raise RuntimeError("Failed to open Docker process stdout")
        
        # Stream container output to WebSocket broker with timeout
        try:
            await asyncio.wait_for(
                stream_process_output_to_broker(
                    session_id=session_id,
                    stdout_iter=process.stdout
                ),
                timeout=MAX_EXECUTION_TIME
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Sandbox container timeout exceeded ({MAX_EXECUTION_TIME}s) for session {session_id}. "
                f"Killing container sandbox-{session_id}."
            )
            
            # Forcefully kill the container via Docker CLI
            kill_proc = await asyncio.create_subprocess_exec(
                "docker", "kill", f"sandbox-{session_id}",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            kill_return = await kill_proc.wait()
            logger.info(f"Docker kill command returned: {kill_return}")
        
        # Wait for Docker process to complete and capture exit code
        return_code = await process.wait()
        logger.info(f"Sandbox container finished for session {session_id} with exit code {return_code}")
        return return_code
    
    except Exception as e:
        logger.error(f"Critical failure in Docker sandbox for session {session_id}: {type(e).__name__}: {str(e)}")
        
        # Attempt cleanup on exception
        if process and process.returncode is None:
            logger.warning(f"Cleaning up Docker process {process.pid} due to exception")
            try:
                kill_proc = await asyncio.create_subprocess_exec(
                    "docker", "kill", f"sandbox-{session_id}",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await asyncio.wait_for(kill_proc.wait(), timeout=5.0)
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup container: {cleanup_error}")
        
        raise


async def check_docker_available() -> bool:
    """Check if Docker is available and accessible.
    
    Returns:
        True if Docker is available, False otherwise
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "docker", "version",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        return_code = await asyncio.wait_for(process.wait(), timeout=5.0)
        return return_code == 0
    except Exception as e:
        logger.error(f"Docker availability check failed: {e}")
        return False


async def ensure_sandbox_network() -> bool:
    """Ensure the sandbox network exists, create if necessary.
    
    Returns:
        True if network is available, False if creation failed
    """
    try:
        # Check if network exists
        process = await asyncio.create_subprocess_exec(
            "docker", "network", "inspect", SANDBOX_NETWORK,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        return_code = await process.wait()
        
        if return_code == 0:
            logger.debug(f"Sandbox network '{SANDBOX_NETWORK}' exists")
            return True
        
        # Network doesn't exist, create it
        logger.info(f"Creating sandbox network '{SANDBOX_NETWORK}'")
        create_proc = await asyncio.create_subprocess_exec(
            "docker", "network", "create",
            "--driver", "bridge",
            SANDBOX_NETWORK,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        create_return = await create_proc.wait()
        return create_return == 0
    
    except Exception as e:
        logger.error(f"Failed to check/create sandbox network: {e}")
        return False
