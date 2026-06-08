from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.services import ml_service
from app.models.recommendation import Recommendation

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


def _mask_phone(num: str) -> str:
    if not num:
        return "anonymous"
    digits = "".join(ch for ch in num if ch.isdigit())
    return f"...{digits[-3:]}" if len(digits) >= 3 else "anonymous"


@router.get("/activity")
def get_activity(
    limit: int = Query(15, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.query(func.count(Recommendation.id)).scalar() or 0

    recent_rows = (
        db.query(Recommendation)
        .order_by(desc(Recommendation.created_at), desc(Recommendation.id))
        .limit(limit)
        .all()
    )
    recent = [{
        "when": r.created_at.isoformat() if r.created_at else None,
        "phone": _mask_phone(r.phone_number),
        "crop": r.crop,
        "district": r.district,
        "decision": r.decision,
        "net_return": r.net_return,
        "language": r.language,
    } for r in recent_rows]

    # breakdowns
    by_decision = dict(
        db.query(Recommendation.decision, func.count(Recommendation.id))
        .group_by(Recommendation.decision).all()
    )
    by_crop = dict(
        db.query(Recommendation.crop, func.count(Recommendation.id))
        .group_by(Recommendation.crop).all()
    )
    by_district = dict(
        db.query(Recommendation.district, func.count(Recommendation.id))
        .group_by(Recommendation.district).all()
    )
    unique_farmers = (
        db.query(func.count(func.distinct(Recommendation.phone_number))).scalar() or 0
    )

    return {
        "total_sessions": total,
        "unique_farmers": unique_farmers,
        "by_decision": by_decision,
        "by_crop": by_crop,
        "by_district": by_district,
        "recent": recent,
    }