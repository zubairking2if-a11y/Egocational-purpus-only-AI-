"""WebSocket route for real-time terminal streaming.

This module handles:
- WebSocket connection acceptance and validation
- Token-based authentication (query param fallback)
- Bidirectional communication (stdout streaming + stdin injection)
- Connection lifecycle management
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from backend.websocket.terminal_processor import ActiveSessionManager
import logging

logger = logging.getLogger("offline-pentest.routes.terminal")

router = APIRouter(prefix="/api/v1/ws", tags=["terminal"])


@router.websocket("/terminal/{session_id}")
async def terminal_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(None)
) -> None:
    """WebSocket endpoint for terminal streaming.
    
    Establishes a bidirectional WebSocket connection for:
    - Broadcasting subprocess stdout to the client (Xterm.js UI)
    - Receiving interactive stdin commands from the client
    
    Authentication:
    - Token passed as query parameter: ?token=<JWT>
    - Validates token format (placeholder—replace with real JWT verification)
    - Closes connection with policy violation if token is invalid
    
    Message Protocol:
    - Server -> Client: Raw terminal output (text frames)
    - Client -> Server: JSON messages {"event": "stdin", "data": "<command>\n"}
    
    Args:
        websocket: FastAPI WebSocket connection
        session_id: Unique session identifier for routing
        token: JWT token passed as query parameter
    """
    # Accept the WebSocket handshake
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for session: {session_id}")
    
    # Simple token validation placeholder
    # TODO: Replace with real JWT verification (see auth/verify_token.py)
    if not token:
        logger.warning(f"No token provided for session {session_id}. Closing connection.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
        return
    
    if token == "invalid_token":
        logger.warning(f"Invalid token provided for session {session_id}. Closing connection.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return
    
    # Register this connection with the session manager
    ActiveSessionManager.register_connection(session_id, websocket)
    
    try:
        while True:
            # Receive data from the client (interactive frames or control messages)
            data = await websocket.receive_json()
            
            if data.get("event") == "stdin":
                user_input = data.get("data", "")
                logger.debug(f"Received stdin for session {session_id}: {repr(user_input[:50])}...")
                # TODO: Inject this into the subprocess stdin if bidirectional mode is enabled
                # await subprocess.stdin.write(user_input.encode())
                
            elif data.get("event") == "ping":
                # Heartbeat/keepalive message
                logger.debug(f"Received keepalive ping from session {session_id}")
                await websocket.send_json({"event": "pong"})
                
            elif data.get("event") == "close":
                # Client requested clean shutdown
                logger.info(f"Client requested session close: {session_id}")
                break
            
            else:
                logger.warning(f"Unknown event type in session {session_id}: {data.get('event')}")
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected gracefully from session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket exception in session {session_id}: {type(e).__name__}: {str(e)}")
    finally:
        # Always clean up the connection
        ActiveSessionManager.remove_connection(session_id, websocket)
        logger.info(f"WebSocket cleanup complete for session: {session_id}")
