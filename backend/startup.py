"""Startup checks and initialization for the backend application."""

import asyncio
import logging
from backend.runner.docker_executor import check_docker_available, ensure_sandbox_network

logger = logging.getLogger("offline-pentest.backend.startup")


async def run_startup_checks() -> bool:
    """Verify Docker and sandbox infrastructure on application startup.
    
    Returns:
        True if all checks pass, False if critical infrastructure is missing
    """
    logger.info("Running backend startup checks...")
    
    # Check Docker availability
    docker_available = await check_docker_available()
    if not docker_available:
        logger.error(
            "Docker is not available. Sandbox execution will fail. "
            "Ensure Docker is installed and the socket is mounted (see docker-compose.sandbox.yml)."
        )
        return False
    
    logger.info("✓ Docker is available")
    
    # Ensure sandbox network exists
    network_ready = await ensure_sandbox_network()
    if not network_ready:
        logger.error("Failed to create/verify sandbox network. Containers may not communicate properly.")
        return False
    
    logger.info("✓ Sandbox network is ready")
    
    logger.info("All startup checks passed")
    return True
