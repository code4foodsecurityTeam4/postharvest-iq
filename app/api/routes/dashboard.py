from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.services import ml_service

router = APIRouter()

@router.get("/summary")
def get_dashboard_summary(
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
):
    districts = ["Tamale", "Bolgatanga", "Wa"]
    crops = ["Maize", "Millet", "Sorghum"]
    summary = []
    for district in districts:
        for crop in crops:
            try:
                rec = ml_service.get_recommendation(
                    crop=crop,
                    district=district,
                    quantity_bags=20,
                    db=db,
                    month=month,
                )
                summary.append({
                    "district":      district,
                    "crop":          crop,
                    "decision":      rec.get("decision"),
                    "current_price": rec.get("current_price"),
                    "forecast_price":rec.get("forecast_price"),
                    "forecast_low":  rec.get("forecast_low"),
                    "forecast_high": rec.get("forecast_high"),
                    "net_per_bag":   rec.get("net_per_bag"),
                    "net_total":     rec.get("net_total"),
                    "method":        rec.get("method"),
                })
            except Exception:
                summary.append({
                    "district": district,
                    "crop": crop,
                    "decision": "UNAVAILABLE",
                    "net_total": None,
                })
    return {"summary": summary, "month": month}