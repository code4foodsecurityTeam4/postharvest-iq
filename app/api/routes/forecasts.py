from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services import ml_service

router = APIRouter()

_VALID_DISTRICTS = {"Tamale", "Bolgatanga", "Wa"}
_VALID_CROPS     = {"Maize", "Millet", "Sorghum"}

@router.get("/{district}/{crop}")
def get_price_forecast(
    district: str,
    crop: str,
    db: Session = Depends(get_db)
):
    if district not in _VALID_DISTRICTS:
        raise HTTPException(status_code=422, detail=f"district must be one of {sorted(_VALID_DISTRICTS)}")
    if crop not in _VALID_CROPS:
        raise HTTPException(status_code=422, detail=f"crop must be one of {sorted(_VALID_CROPS)}")
    forecast = ml_service.get_forecast(
        district=district,
        crop=crop,
        db=db
    )
    return {"forecast": forecast}