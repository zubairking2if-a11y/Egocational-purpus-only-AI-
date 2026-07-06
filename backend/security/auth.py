"""JWT token verification and validation for WebSocket authentication.

This module provides utilities to:
- Decode and validate JWT tokens
- Check token expiration
- Raise appropriate WebSocket exceptions on validation failure

Configuration:
- JWT_SECRET_KEY: Override via environment variable (default: development key)
- JWT_ALGORITHM: Override via environment variable (default: HS256)
"""

import os
import jwt
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from fastapi import WebSocketException, status
import logging

logger = logging.getLogger("offline-pentest.security.auth")

# Load configuration from environment variables
# In production, these MUST be set via secure environment variable management
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-pentest-key-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))

# Log warning if using development defaults
if JWT_SECRET_KEY == "your-super-secret-pentest-key-change-me":
    logger.warning(
        "Using development JWT secret key. "
        "Set JWT_SECRET_KEY environment variable in production!"
    )


def verify_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token.
    
    Performs the following validation:
    1. Verifies JWT signature using the configured secret and algorithm
    2. Checks token expiration timestamp (exp claim)
    3. Returns the decoded payload on success
    
    Args:
        token: JWT token string to validate
    
    Returns:
        Decoded JWT payload dictionary containing claims (sub, exp, iat, etc.)
    
    Raises:
        WebSocketException: On any validation failure (invalid signature, expired, malformed)
                           Closes connection with WS_1008_POLICY_VIOLATION code
    
    Example:
        try:
            payload = verify_access_token(token_from_query_param)
            user_id = payload["sub"]  # Subject (typically user ID)
            session_data = payload.get("session_id")  # Custom claims
        except WebSocketException as e:
            # Token validation failed - connection will be closed
            logger.error(f"Auth failed: {e.reason}")
    """
    try:
        # Decode and verify JWT signature
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )
        
        # Explicitly check expiration (jwt library should do this, but be defensive)
        exp = payload.get("exp")
        if exp is not None:
            current_time = datetime.now(timezone.utc).timestamp()
            if current_time > exp:
                logger.warning(f"Token expired at {datetime.fromtimestamp(exp, tz=timezone.utc)}")
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Token expired"
                )
        
        logger.debug(f"Token verified successfully for user: {payload.get('sub')}")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token validation failed: Signature expired")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Token expired"
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"Token validation failed: {type(e).__name__}: {str(e)}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid authentication token"
        )
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {type(e).__name__}: {str(e)}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication validation failed"
        )


def create_access_token(
    subject: str,
    expires_in_minutes: int = None,
    additional_claims: Dict[str, Any] = None
) -> str:
    """Create a new JWT access token for development/testing.
    
    Args:
        subject: Subject claim (typically user ID or session ID)
        expires_in_minutes: Token lifetime in minutes (default: from JWT_EXPIRATION_MINUTES env var)
        additional_claims: Dictionary of extra claims to include in payload
    
    Returns:
        Encoded JWT token string
    
    Note:
        This is primarily for development/testing. In production, tokens should be
        issued by a dedicated auth service (OAuth2, etc.)
    
    Example:
        token = create_access_token("user-123", additional_claims={"session_id": "sess-456"})
        # Use token in WebSocket connection: ws://host/api/v1/ws/terminal/sess-456?token={token}
    """
    if expires_in_minutes is None:
        expires_in_minutes = JWT_EXPIRATION_MINUTES
    
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_in_minutes)).timestamp()),
    }
    
    if additional_claims:
        payload.update(additional_claims)
    
    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )
    
    logger.debug(f"Created access token for subject: {subject}, expires in {expires_in_minutes} minutes")
    return token
