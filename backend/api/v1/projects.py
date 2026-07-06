from fastapi import APIRouter

router = APIRouter()

@router.get("/projects")
async def list_projects():
    return []
