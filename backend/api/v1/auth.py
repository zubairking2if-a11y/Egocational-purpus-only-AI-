from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post("/login")
async def login():
    # placeholder: return a dummy token
    return {"access_token": "REPLACE_ME_TOKEN", "token_type": "bearer"}
