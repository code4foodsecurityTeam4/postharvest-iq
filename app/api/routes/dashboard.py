from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services import ml_service, storage_service

router = APIRouter()

@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    districts = ["Sagnarigu", "Tolon", "Kumbungu", "Tamale"]
    crops = ["Maize", "Millet", "Sorghum"]
    summary = []
    for district in districts:
        for crop in crops:
            try:
                rec = ml_service.get_recommendation(
                    crop=crop,
                    district=district,
                    quantity_bags=20,
                    db=db
                )
                summary.append({
                    "district": district,
                    "crop": crop,
                    "decision": rec.get("decision"),
                    "net_total": rec.get("net_total"),
                    "forecast_price": rec.get("forecast_price"),
                    "current_price": rec.get("current_price"),
                })
            except Exception:
                summary.append({
                    "district": district,
                    "crop": crop,
                    "decision": "UNAVAILABLE",
                    "net_total": None,
                })
    return {"summary": summary}