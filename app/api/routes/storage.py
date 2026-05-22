from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services import storage_service

router = APIRouter()

@router.get("/{district}/{crop}")
def get_nearest_storage(
    district: str,
    crop: str,
    db: Session = Depends(get_db)
):
    results = storage_service.get_nearest_storage(
        district=district,
        crop=crop,
        db=db
    )
    return {"storage_locations": results}