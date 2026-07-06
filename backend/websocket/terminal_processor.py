"""Terminal processor: reads raw bytes from async process streams and broadcasts to WebSocket clients.

This module handles:
- Reading chunks from async subprocess streams
- Decoding UTF-8 safely with surrogate escape handling
- Broadcasting to active WebSocket sessions via ActiveSessionManager
"""

import asyncio
import logging
from typing import Dict, List

logger = logging.getLogger("offline-pentest.websocket.terminal_processor")


class ActiveSessionManager:
    """Manages active live WebSocket connections for terminal streaming.
    
    Maintains a registry of active WebSocket connections per session ID
    and provides broadcast primitives for pushing terminal output to all
    connected clients.
    """
    _active_connections: Dict[str, List] = {}

    @classmethod
    def register_connection(cls, session_id: str, websocket) -> None:
        """Register a new WebSocket connection for a session.
        
        Args:
            session_id: Unique identifier for the session
            websocket: FastAPI WebSocket connection object
        """
        if session_id not in cls._active_connections:
            cls._active_connections[session_id] = []
        cls._active_connections[session_id].append(websocket)
        logger.debug(f"Registered connection for session {session_id}. "
                     f"Active clients: {len(cls._active_connections[session_id])}")

    @classmethod
    def remove_connection(cls, session_id: str, websocket) -> None:
        """Remove a WebSocket connection from a session.
        
        Args:
            session_id: Unique identifier for the session
            websocket: FastAPI WebSocket connection object to remove
        """
        if session_id in cls._active_connections:
            try:
                cls._active_connections[session_id].remove(websocket)
                logger.debug(f"Removed connection from session {session_id}. "
                             f"Remaining clients: {len(cls._active_connections[session_id])}")
                
                # Clean up empty session entries
                if not cls._active_connections[session_id]:
                    del cls._active_connections[session_id]
                    logger.info(f"Session {session_id} has no active connections.")
            except ValueError:
                logger.warning(f"Attempted to remove non-existent connection from session {session_id}")

    @classmethod
    async def broadcast_to_session(cls, session_id: str, message: str) -> None:
        """Broadcast a message to all active clients in a session.
        
        Args:
            session_id: Target session ID
            message: Text message to broadcast (typically terminal output)
        """
        if session_id not in cls._active_connections:
            logger.debug(f"No active connections for session {session_id}")
            return
        
        # Gather all send coroutines for this session
        connections = cls._active_connections[session_id]
        if not connections:
            return
        
        coros = [ws.send_text(message) for ws in connections]
        
        # Execute all sends in parallel, capturing individual exceptions
        results = await asyncio.gather(*coros, return_exceptions=True)
        
        # Log any failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to send to client {i} in session {session_id}: {result}")

    @classmethod
    def get_session_count(cls) -> int:
        """Return the number of active sessions."""
        return len(cls._active_connections)

    @classmethod
    def get_connection_count(cls, session_id: str = None) -> int:
        """Return connection count for a specific session or all sessions.
        
        Args:
            session_id: If provided, count only this session. Otherwise, count total.
        """
        if session_id:
            return len(cls._active_connections.get(session_id, []))
        return sum(len(conns) for conns in cls._active_connections.values())


async def stream_process_output_to_broker(session_id: str, stdout_iter: asyncio.StreamReader) -> None:
    """Read chunks from async subprocess stream and broadcast to WebSocket clients.
    
    This function:
    1. Reads 4KB chunks from the subprocess stdout
    2. Decodes UTF-8 safely (with surrogateescape for binary artifacts)
    3. Broadcasts decoded text to all WebSocket clients in the session
    4. Handles graceful shutdown and error logging
    
    Args:
        session_id: Unique session identifier for routing messages
        stdout_iter: asyncio.StreamReader connected to subprocess stdout
    """
    logger.info(f"Starting terminal stream broker for session: {session_id}")
    chunk_count = 0
    total_bytes = 0
    
    try:
        # Read in 4KB chunks to maintain low latency and high throughput
        while True:
            chunk = await stdout_iter.read(4096)
            if not chunk:
                logger.info(f"End of stream reached for session {session_id}")
                break
            
            chunk_count += 1
            total_bytes += len(chunk)
            
            # Decode using surrogateescape to prevent crashes on raw binary artifacts
            # This preserves unpaired surrogates as placeholder characters
            text_frame = chunk.decode("utf-8", errors="surrogateescape")
            
            # Broadcast to all connected clients in this session
            await ActiveSessionManager.broadcast_to_session(session_id, text_frame)
            
            if chunk_count % 10 == 0:
                logger.debug(f"Session {session_id}: {chunk_count} chunks, {total_bytes} bytes processed")
                
    except asyncio.CancelledError:
        logger.warning(f"Stream interrupted for session: {session_id} after {chunk_count} chunks")
    except Exception as e:
        logger.error(f"Error in terminal stream processor for session {session_id}: {type(e).__name__}: {str(e)}")
    finally:
        logger.info(f"Terminal stream broker closed for session: {session_id} "
                    f"({chunk_count} chunks, {total_bytes} bytes total)")
