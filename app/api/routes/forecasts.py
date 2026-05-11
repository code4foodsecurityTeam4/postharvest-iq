from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_forecasts():
    return {"message": "Forecasts endpoint ready"}