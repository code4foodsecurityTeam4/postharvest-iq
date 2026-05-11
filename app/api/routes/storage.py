from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_storage():
    return {"message": "Storage endpoint ready"}