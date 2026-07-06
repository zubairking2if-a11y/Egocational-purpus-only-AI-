"""Subprocess execution framework for pentesting tools.

This module provides:
- Safe command validation and sanitization
- Async subprocess execution with timeout enforcement
- Real-time output streaming to WebSocket broker
- Security policy enforcement (blocked keywords, execution limits)
"""

import asyncio
import os
import shlex
import logging
from typing import List

from backend.websocket.terminal_processor import stream_process_output_to_broker

logger = logging.getLogger("offline-pentest.runner.executor")

# Configuration limits for security mitigation
MAX_EXECUTION_TIME = int(os.getenv("SANDBOX_MAX_EXEC_TIME", "300"))

# Blocked keywords to prevent command injection and dangerous operations
BLOCKED_KEYWORDS = {
    "rm",      # Remove files (prevent data destruction)
    "chmod",   # Change permissions (prevent privilege escalation)
    "chown",   # Change owner (prevent privilege escalation)
    "wget",    # Download (prevent external data exfiltration)
    "curl",    # Download (prevent external data exfiltration)
    "bash",    # Shell (prevent shell escape)
    "sh",      # Shell (prevent shell escape)
    ";",       # Command separator (prevent injection)
    "&&",      # Logical AND (prevent injection)
    "||",      # Logical OR (prevent injection)
    ">",       # Redirect (prevent file manipulation)
    "<",       # Redirect (prevent file manipulation)
    "|",       # Pipe (prevent injection)
}


def validate_command(command_list: List[str]) -> bool:
    """Sanitize and evaluate the target binary and execution flags.
    
    Mitigates local command injection vectors by:
    1. Checking for explicitly blocked keywords
    2. Validating command structure
    3. Preventing shell metacharacter escapes
    
    Args:
        command_list: Parsed command arguments (result of shlex.split)
    
    Returns:
        True if command passes validation, False otherwise
    
    Example:
        >>> validate_command(['nmap', '-sV', 'example.com'])
        True
        >>> validate_command(['rm', '-rf', '/'])
        False
    """
    if not command_list:
        logger.warning("Command validation failed: Empty command list")
        return False
    
    # Check each command element against blocked keywords
    for element in command_list:
        normalized = element.strip().lower()
        
        # Exact match check
        if normalized in BLOCKED_KEYWORDS:
            logger.warning(f"Security Policy Rejection: Blocked keyword detected: {element}")
            return False
        
        # Substring check for injection attempts (e.g., "command;rm -rf /")
        for blocked in BLOCKED_KEYWORDS:
            if blocked in normalized and blocked not in ["", "."]:
                logger.warning(f"Security Policy Rejection: Blocked pattern '{blocked}' found in: {element}")
                return False
    
    return True


async def run_pentest_tool(session_id: str, raw_command: str) -> int:
    """Parse, validate, and spawn an isolated tool execution process.
    
    This function:
    1. Safely parses command arguments using shlex (no shell execution)
    2. Validates command against security policy (blocked keywords)
    3. Spawns subprocess with stderr merged into stdout
    4. Streams all output directly to the WebSocket broker
    5. Enforces execution timeout and process cleanup
    
    Args:
        session_id: Unique session identifier for routing output
        raw_command: Raw command string (e.g., "nmap -sV example.com")
    
    Returns:
        Process exit code (0 = success, non-zero = failure)
    
    Raises:
        ValueError: If command fails validation
        Exception: If subprocess execution fails
    
    Example:
        exit_code = await run_pentest_tool("sess-123", "nmap -sV -p 22,80 example.com")
    """
    # Use shlex to safely split command arguments without shell execution vulnerabilities
    try:
        command_list = shlex.split(raw_command)
    except ValueError as e:
        logger.error(f"Command parse failure for session {session_id}: {str(e)}")
        raise ValueError(f"Invalid command syntax: {str(e)}")
    
    # Validate command against security policy
    if not validate_command(command_list):
        raise ValueError("Command execution rejected due to security policy violations.")
    
    logger.info(f"Starting pentest tool execution for session {session_id}: {command_list[0]}")
    logger.debug(f"Full command: {' '.join(command_list)}")
    
    process = None
    try:
        # Spawn process directly without shell=True to avoid execution injections
        # stderr is merged with stdout for sequential terminal output
        process = await asyncio.create_subprocess_exec(
            *command_list,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # Merge stderr into stdout for xterm processing
            env={
                "TERM": "xterm-256color",       # Color capability support
                "PATH": os.getenv("PATH", "/usr/bin:/bin")
            }
        )
        
        logger.debug(f"Process spawned with PID {process.pid} for session {session_id}")
        
        if not process.stdout:
            logger.error(f"Failed to open stdout for session {session_id}")
            raise RuntimeError("Process stdout stream is unavailable")
        
        # Stream output to WebSocket broker with timeout enforcement
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
                f"Execution timeout exceeded ({MAX_EXECUTION_TIME}s) for session {session_id}. "
                f"Terminating process (PID {process.pid})."
            )
            process.terminate()
            
            # Wait for graceful termination, then kill if necessary
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"Process {process.pid} did not terminate gracefully. Killing.")
                process.kill()
                await process.wait()
        
        # Capture process exit status
        return_code = await process.wait()
        logger.info(f"Process {process.pid} completed with exit code {return_code} for session {session_id}")
        return return_code
    
    except Exception as e:
        logger.error(f"Execution failure in runner for session {session_id}: {type(e).__name__}: {str(e)}")
        
        # Ensure process cleanup on exception
        if process and process.returncode is None:
            logger.warning(f"Cleaning up process {process.pid} due to exception")
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        
        raise
