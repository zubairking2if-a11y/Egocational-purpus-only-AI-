"""Rate limiting middleware (placeholder)."""
from fastapi import Request

async def rate_limit(request: Request, call_next):
    return await call_next(request)
