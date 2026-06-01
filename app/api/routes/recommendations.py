from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.services import ml_service

router = APIRouter()

class RecommendationRequest(BaseModel):
    crop: str
    district: str
    quantity_bags: int = 20
    language: str = "en"
    phone_number: str = ""
    session_id: str = ""
    month: Optional[int] = None   # demo override; defaults to current month

@router.post("/")
def get_recommendation(
    request: RecommendationRequest,
    db: Session = Depends(get_db)
):
    result = ml_service.get_recommendation(
        crop=request.crop,
        district=request.district,
        quantity_bags=request.quantity_bags,
        language=request.language,
        phone_number=request.phone_number,
        session_id=request.session_id,
        db=db,
        month=request.month,
    )
    return result