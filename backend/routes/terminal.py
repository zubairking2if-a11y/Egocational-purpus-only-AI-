"""WebSocket route for real-time terminal streaming.

This module handles:
- WebSocket connection acceptance and validation
- JWT token-based authentication (query param)
- Bidirectional communication (stdout streaming + stdin injection)
- Connection lifecycle management
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, WebSocketException, status
from backend.websocket.terminal_processor import ActiveSessionManager
from backend.security.auth import verify_access_token
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
    - Validates JWT signature, algorithm, and expiration
    - Closes connection with WS_1008_POLICY_VIOLATION if token is invalid
    
    Message Protocol:
    - Server -> Client: Raw terminal output (text frames)
    - Client -> Server: JSON messages {"event": "stdin", "data": "<command>\\n"}
                         or {"event": "ping"} for keepalive
    
    Args:
        websocket: FastAPI WebSocket connection
        session_id: Unique session identifier for routing
        token: JWT token passed as query parameter
    
    Raises:
        WebSocketException: If token validation fails (handled and closed gracefully)
    """
    # Enforce token check BEFORE accepting the handshake
    if not token:
        logger.warning(f"No token provided for session {session_id}. Rejecting connection.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
        return
    
    try:
        # Securely decode and verify JWT payload
        token_payload = verify_access_token(token)
        user_id = token_payload.get("sub", "unknown")
        logger.info(f"User {user_id} authenticated successfully for session {session_id}")
        
        # Accept connection only after successful validation
        await websocket.accept()
        
    except WebSocketException as e:
        # Token validation failed—close with appropriate code and reason
        logger.error(f"WebSocket auth rejection for session {session_id}: {e.reason}")
        await websocket.close(code=e.code, reason=e.reason)
        return
    except Exception as e:
        # Unexpected error during validation
        logger.error(f"Unexpected error during token validation: {type(e).__name__}: {str(e)}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication validation failed")
        return
    
    # Register this authenticated connection with the session manager
    ActiveSessionManager.register_connection(session_id, websocket)
    logger.info(f"WebSocket client authorized for session: {session_id}")
    
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
