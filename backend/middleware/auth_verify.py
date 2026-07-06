"""Middleware: auth verification placeholder."""
from fastapi import Request

async def auth_verify(request: Request, call_next):
    # Very small placeholder: in production validate JWTs & RBAC
    return await call_next(request)
