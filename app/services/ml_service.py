import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.services.recommendation_service import calculate_net_return
from app.services import storage_service
from app.models.recommendation import Recommendation

MARKET_FOR_DISTRICT = {
    "Sagnarigu": "Tamale",
    "Tolon":     "Tamale",
    "Kumbungu":  "Kumbungu",
    "Tamale":    "Tamale",
}

def get_current_price(crop: str, district: str, db: Session) -> float:
    market = MARKET_FOR_DISTRICT.get(district, "Tamale")
    result = db.execute(text("""
        SELECT price FROM wfp_prices
        WHERE commodity = :crop
        AND market = :market
        AND pricetype = 'Wholesale'
        ORDER BY date DESC
        LIMIT 1
    """), {"crop": crop, "market": market}).fetchone()
    return float(result[0]) if result else 180.0

def get_recent_prices(
    crop: str, district: str, db: Session, n: int = 6
) -> list:
    market = MARKET_FOR_DISTRICT.get(district, "Tamale")
    rows = db.execute(text("""
        SELECT price, date FROM wfp_prices
        WHERE commodity = :crop
        AND market = :market
        AND pricetype = 'Wholesale'
        ORDER BY date DESC
        LIMIT :n
    """), {"crop": crop, "market": market, "n": n}).fetchall()
    return [float(r[0]) for r in rows]

def get_forecast(
    crop: str, district: str, db: Session
) -> dict:
    # Placeholder until LSTM/XGBoost models are trained
    # Returns a simple seasonal estimate based on recent prices
    prices = get_recent_prices(crop, district, db)
    if not prices:
        return {"forecast_price": 220.0, "method": "fallback"}
    current = prices[0]
    # Simple seasonal uplift estimate — 25% rise expected at lean season
    forecast = round(current * 1.25, 2)
    return {
        "forecast_price": forecast,
        "current_price":  current,
        "method":         "seasonal_estimate"
    }

def get_recommendation(
    crop: str,
    district: str,
    quantity_bags: int = 20,
    language: str = "en",
    phone_number: str = "",
    session_id: str = "",
    db: Session = None,
    storage_cost_per_bag_month: float = 6.0,
) -> dict:
    current_price = get_current_price(crop, district, db)
    forecast_data = get_forecast(crop, district, db)
    forecast_price = forecast_data.get("forecast_price", current_price * 1.25)

    decision_data = calculate_net_return(
        current_price=current_price,
        forecast_price=forecast_price,
        quantity_bags=quantity_bags,
        storage_cost_per_bag_month=storage_cost_per_bag_month,
    )

    storage = storage_service.get_nearest_storage(
        district=district, crop=crop, db=db
    )

    # Log recommendation to MySQL
    if db and phone_number:
        rec = Recommendation(
            session_id=session_id,
            phone_number=phone_number,
            language=language,
            crop=crop,
            district=district,
            quantity_bags=quantity_bags,
            current_price=current_price,
            forecast_price=forecast_price,
            decision=decision_data["decision"],
            net_return=decision_data["net_total"],
            storage_id=None,
        )
        db.add(rec)
        db.commit()

    return {
        "decision":       decision_data["decision"],
        "current_price":  current_price,
        "forecast_price": forecast_price,
        "expected_gain":  decision_data["expected_gain"],
        "net_per_bag":    decision_data["net_per_bag"],
        "net_total":      decision_data["net_total"],
        "crop":           crop,
        "district":       district,
        "storage":        storage[0] if storage else None,
        "method":         forecast_data.get("method"),
    }