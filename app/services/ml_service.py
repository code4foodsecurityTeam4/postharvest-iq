"""
app/services/ml_service.py
"""

import math
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.recommendation_service import calculate_net_return
from app.services import storage_service
from app.models.recommendation import Recommendation


MARKET_FOR_DISTRICT = {
    "Sagnarigu": "Tamale",
    "Tolon":     "Tamale",
    "Kumbungu":  "Tamale",   # no WFP price data for Kumbungu market; Tamale is nearest
    "Tamale":    "Tamale",
}

VALID_MARKETS     = {"Bolga", "Kumasi", "Tamale", "Techiman", "Wa"}
VALID_COMMODITIES = {"Maize", "Millet", "Sorghum"}

# Documented Northern Ghana cereal seasonality (fractional expected
# change to next-period price). Harvest (Oct-Dec): prices low, recovery
# ahead. Lean (Jun-Aug): prices near peak, little upside to storing.
SEASONAL_UPLIFT = {
    1: 0.05, 2: 0.03, 3: 0.0,  4: -0.03, 5: -0.05, 6: -0.08,
    7: -0.08, 8: -0.05, 9: 0.08, 10: 0.22, 11: 0.20, 12: 0.12,
}

_ml_ready = False

def _load_ml():
    """Load trained models on first use. Returns True if successful."""
    global _ml_ready
    if _ml_ready:
        return True
    try:
        from app.ml import predict as _predict   # noqa: F401
        _ml_ready = True
        return True
    except Exception as e:
        print(f"[ml_service] ML models not loaded: {e}")
        return False


def _get_macro_features(db: Session, commodity: str, month: int) -> dict:
    """Fetch latest exchange rate and producer price index from MySQL."""
    fx_row = db.execute(text("""
        SELECT value FROM ghana_exchange_rates
        WHERE months != 'Annual value'
          AND element = 'Local currency units per USD'
        ORDER BY year DESC, months DESC
        LIMIT 1
    """)).fetchone()
    exchange_rate = float(fx_row[0]) if fx_row else 10.0

    pp_row = db.execute(text("""
        SELECT value FROM fao_producer_prices
        WHERE item    = :commodity
          AND months  = 'Annual value'
          AND element = 'Producer Price Index (2014-2016 = 100)'
        ORDER BY year DESC
        LIMIT 1
    """), {"commodity": commodity}).fetchone()

    if not pp_row:
        pp_row = db.execute(text("""
            SELECT AVG(value) FROM fao_producer_prices
            WHERE item IN ('Millet','Sorghum')
              AND months  = 'Annual value'
              AND element = 'Producer Price Index (2014-2016 = 100)'
              AND year = (SELECT MAX(year) FROM fao_producer_prices)
        """)).fetchone()

    producer_price_index = float(pp_row[0]) if pp_row and pp_row[0] else 100.0

    return {
        "exchange_rate":        exchange_rate,
        "producer_price_index": producer_price_index,
    }


def get_current_price(crop: str, district: str, db: Session) -> float:
    market = MARKET_FOR_DISTRICT.get(district, "Tamale")
    result = db.execute(text("""
        SELECT price FROM wfp_prices
        WHERE commodity = :crop
          AND market    = :market
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
          AND market    = :market
          AND pricetype = 'Wholesale'
        ORDER BY date DESC
        LIMIT :n
    """), {"crop": crop, "market": market, "n": n}).fetchall()
    return [float(r[0]) for r in rows]


def get_forecast(crop: str, district: str, db: Session) -> dict:
    """
    Estimate next-period price using a documented seasonal heuristic.

    The trained LSTM/XGBoost pipeline is validated but not used for live
    forecasts: available WFP VAM price data ends at the July 2023 inflation
    peak, so model forecasts anchored there are unreliable for 2026. This
    seasonal heuristic reflects the documented Oct-Jan recovery pattern in
    Northern Ghana cereals and is the interim live method until current
    price data is obtained and the models are retrained.
    """
    import datetime
    prices = get_recent_prices(crop, district, db)
    if not prices:
        return {"forecast_price": 220.0, "current_price": 180.0, "method": "fallback"}
    current = prices[0]
    month = datetime.datetime.now().month
    uplift = SEASONAL_UPLIFT.get(month, 0.0)
    return {
        "forecast_price": round(current * (1 + uplift), 2),
        "current_price": current,
        "method": "seasonal_heuristic",
    }


def get_recommendation(
    crop: str,
    district: str,
    quantity_bags: int = 20,
    language: str = "en",
    phone_number: str = "",
    session_id: str = "",
    db: Session = None,
    storage_cost_per_bag_month: float = 0.80,
) -> dict:
    """
    Full recommendation pipeline.

    Decision source: rule-based net-return calculation (calculate_net_return),
    driven by a seasonal price heuristic. The trained XGBoost classifier is
    run for comparison/telemetry only (ml_confidence, ml_all_probs) and does
    NOT override the rule-based decision, because available price data ends
    in 2023 and model forecasts are not reliable for current dates.
    """
    market        = MARKET_FOR_DISTRICT.get(district, "Tamale")
    current_price = get_current_price(crop, district, db)
    forecast_data = get_forecast(crop, district, db)
    forecast_price = forecast_data.get("forecast_price", current_price * 1.25)

    # calculate net return using rule-based formula
    decision_data = calculate_net_return(
        current_price              = current_price,
        forecast_price             = forecast_price,
        quantity_bags              = quantity_bags,
        storage_cost_per_bag_month = storage_cost_per_bag_month,
    )

    # ML classifier decision
    ml_decision   = None
    ml_confidence = None
    ml_all_probs  = None
    ml_model_used = None

    if (_load_ml() and market in VALID_MARKETS
            and crop in VALID_COMMODITIES and db is not None):
        try:
            from app.ml.predict import predict_decision
            import datetime

            month = datetime.datetime.now().month
            macro = _get_macro_features(db, crop, month)

            prices = get_recent_prices(crop, district, db, n=13)
            lag1   = prices[1] if len(prices) > 1 else current_price
            lag2   = prices[2] if len(prices) > 2 else lag1
            lag3   = prices[3] if len(prices) > 3 else lag2

            rolling_mean = float(np.mean([current_price, lag1, lag2]))
            rolling_std  = float(np.std( [current_price, lag1, lag2]))
            pct_change   = (current_price - lag1) / lag1 if lag1 != 0 else 0.0

            is_harvest = 1 if month in [10, 11, 12] else 0
            is_lean    = 1 if month in [6, 7, 8]    else 0

            annual_avg   = float(np.mean(prices[:12])) if len(prices) >= 12 else current_price
            price_vs_ann = current_price / annual_avg if annual_avg != 0 else 1.0
            price_yoy    = ((current_price - prices[12]) / prices[12]
                            if len(prices) >= 13 else 0.0)

            feat_row = {
                "market":               market,
                "commodity":            crop,
                "price_lag1":           lag1,
                "price_lag2":           lag2,
                "price_lag3":           lag3,
                "rolling_mean_3":       rolling_mean,
                "rolling_std_3":        rolling_std,
                "price_pct_change":     pct_change,
                "exchange_rate":        macro["exchange_rate"],
                "producer_price_index": macro["producer_price_index"],
                "month_sin":            math.sin(2 * math.pi * month / 12),
                "month_cos":            math.cos(2 * math.pi * month / 12),
                "is_harvest_season":    is_harvest,
                "is_lean_season":       is_lean,
                "price_vs_annual":      price_vs_ann,
                "price_yoy":            price_yoy,
            }

            feat_df   = pd.DataFrame([feat_row])
            result    = predict_decision(feat_df)
            ml_decision   = result["decision"]
            ml_confidence = result["confidence"]
            ml_all_probs  = result["all_probs"]
            ml_model_used = result["model_used"]

        except Exception as e:
            print(f"[ml_service] Classifier prediction failed, using fallback: {e}")

    # use ML decision if available otherwise use rule-based
    final_decision = decision_data["decision"]
    
    # find nearest storage
    storage = storage_service.get_nearest_storage(
        district=district, crop=crop, db=db
    )

    # log recommendation to MySQL
    if db and phone_number:
        try:
            rec = Recommendation(
                session_id    = session_id,
                phone_number  = phone_number,
                language      = language,
                crop          = crop,
                district      = district,
                quantity_bags = quantity_bags,
                current_price = current_price,
                forecast_price= forecast_price,
                decision      = final_decision,
                net_return    = decision_data["net_total"],
                storage_id    = None,
            )
            db.add(rec)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[ml_service] Failed to log recommendation: {e}")

    return {
        "decision":      final_decision,
        "current_price": current_price,
        "forecast_price":forecast_price,
        "expected_gain": decision_data["expected_gain"],
        "net_per_bag":   decision_data["net_per_bag"],
        "net_total":     decision_data["net_total"],
        "crop":          crop,
        "district":      district,
        "storage":       storage[0] if storage else None,
        "method":        forecast_data.get("method"),
        "ml_confidence": ml_confidence,
        "ml_all_probs":  ml_all_probs,
        "ml_model_used": ml_model_used,
    }