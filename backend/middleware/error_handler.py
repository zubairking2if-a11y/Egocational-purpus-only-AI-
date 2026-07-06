"""Global error handler placeholder."""
from fastapi import Request

async def handle_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        return {"error": str(e)}
