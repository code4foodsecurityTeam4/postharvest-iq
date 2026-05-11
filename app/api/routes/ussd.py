from fastapi import APIRouter

router = APIRouter()

@router.post("/")
async def ussd_callback():
    return {"message": "USSD endpoint ready"}