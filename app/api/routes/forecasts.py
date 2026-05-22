from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services import ml_service

router = APIRouter()

@router.get("/{district}/{crop}")
def get_price_forecast(
    district: str,
    crop: str,
    db: Session = Depends(get_db)
):
    forecast = ml_service.get_forecast(
        district=district,
        crop=crop,
        db=db
    )
    return {"forecast": forecast}