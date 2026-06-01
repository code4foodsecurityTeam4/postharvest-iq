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
    "Kumbungu":  "Kumbungu",
    "Tamale":    "Tamale",
}

# Valid markets and commodities the model was trained on 
VALID_MARKETS     = {"Bolga", "Kumasi", "Tamale", "Techiman", "Wa"}
VALID_COMMODITIES = {"Maize", "Millet", "Sorghum"}

# ── Lazy-load ML models — only imported when first needed to avoid slowing down FastAPI startup and to allow the app to run even if model files are missing.
# This prevents the app from crashing at startup if model files are missing.
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


#  Helper: fetch exchange rate and producer price index 

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
        "exchange_rate":         exchange_rate,
        "producer_price_index":  producer_price_index,
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
    Forecast next month's price using the trained multivariate LSTM.

    Falls back to the original seasonal estimate (×1.25) if:
      - ML models are not loaded yet
      - Not enough price history exists (< 12 months)
      - The market is not in the model's training set
    """
    market = MARKET_FOR_DISTRICT.get(district, "Tamale")

    #  Attempt real LSTM forecast 
    if _load_ml() and market in VALID_MARKETS and crop in VALID_COMMODITIES:
        try:
            from app.ml.predict import forecast_price
            from app.ml.config  import LSTM_SEQ_LEN, LSTM_FEAT_COLS

            # Fetch price history with all LSTM features
            rows = db.execute(text("""
                SELECT
                    p.date,
                    p.price,
                    COALESCE(fx.value, 10.0)    AS exchange_rate,
                    COALESCE(pp.value, 100.0)   AS producer_price_index,
                    SIN(2*PI()*MONTH(p.date)/12) AS month_sin,
                    COS(2*PI()*MONTH(p.date)/12) AS month_cos
                FROM wfp_prices p
                LEFT JOIN ghana_exchange_rates fx
                    ON fx.year   = YEAR(p.date)
                    AND fx.months = DATE_FORMAT(p.date, '%M')
                    AND fx.element = 'Local currency units per USD'
                LEFT JOIN fao_producer_prices pp
                    ON pp.year  = YEAR(p.date)
                    AND pp.item = p.commodity
                    AND pp.months  = 'Annual value'
                    AND pp.element = 'Producer Price Index (2014-2016 = 100)'
                WHERE p.market    = :market
                  AND p.commodity = :crop
                  AND p.pricetype = 'Wholesale'
                ORDER BY p.date DESC
                LIMIT :limit
            """), {"market": market, "crop": crop,
                   "limit": LSTM_SEQ_LEN + 5}).fetchall()

            if len(rows) >= LSTM_SEQ_LEN:
                df = pd.DataFrame(rows, columns=[
                    'date','price','exchange_rate','producer_price_index',
                    'month_sin','month_cos'
                ])
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)

                # Compute lag features
                df['price_lag1']     = df['price'].shift(1)
                df['price_lag2']     = df['price'].shift(2)
                df['price_lag3']     = df['price'].shift(3)
                df['rolling_mean_3'] = df['price'].rolling(3, min_periods=1).mean()
                df['rolling_std_3']  = df['price'].rolling(3, min_periods=2).std()
                df = df.dropna(subset=['price_lag1','price_lag2',
                                       'price_lag3','rolling_std_3'])

                if len(df) >= LSTM_SEQ_LEN:
                    predicted_price = forecast_price(df)
                    current_price   = float(df.iloc[-1]['price'])
                    return {
                        "forecast_price": predicted_price,
                        "current_price":  current_price,
                        "method":         "lstm",
                    }

        except Exception as e:
            print(f"[ml_service] LSTM forecast failed, using fallback: {e}")

    # Fallback: original seasonal estimate
    prices = get_recent_prices(crop, district, db)
    if not prices:
        return {"forecast_price": 220.0, "current_price": 180.0, "method": "fallback"}
    current = prices[0]
    forecast = round(current * 1.25, 2)
    return {
        "forecast_price": forecast,
        "current_price":  current,
        "method":         "seasonal_estimate",
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

    Decision source (in priority order):
      1. Trained XGBoost/RF classifier (if models loaded and market valid)
      2. calculate_net_return()

    Net return figures always come from calculate_net_return() — this keeps
    the financial logic in one place and avoids discrepancies between the two decision sources.
    """
    market         = MARKET_FOR_DISTRICT.get(district, "Tamale")
    current_price  = get_current_price(crop, district, db)
    forecast_data  = get_forecast(crop, district, db)
    forecast_price = forecast_data.get("forecast_price", current_price * 1.25)

    #  Net return 
    decision_data = calculate_net_return(
        current_price              = current_price,
        forecast_price             = forecast_price,
        quantity_bags              = quantity_bags,
        storage_cost_per_bag_month = storage_cost_per_bag_month,
    )

    #  ML classifier decision (replaces rule-based decision if available) 
    ml_decision    = None
    ml_confidence  = None
    ml_all_probs   = None
    ml_model_used  = None

    if (_load_ml() and market in VALID_MARKETS
            and crop in VALID_COMMODITIES and db is not None):
        try:
            from app.ml.predict import predict_decision
            import datetime

            month = datetime.datetime.now().month
            macro = _get_macro_features(db, crop, month)

            # Get lag prices
            prices = get_recent_prices(crop, district, db, n=13)
            lag1   = prices[1] if len(prices) > 1 else current_price
            lag2   = prices[2] if len(prices) > 2 else lag1
            lag3   = prices[3] if len(prices) > 3 else lag2

            rolling_mean = float(np.mean([current_price, lag1, lag2]))
            rolling_std  = float(np.std( [current_price, lag1, lag2]))
            pct_change   = (current_price - lag1) / lag1 if lag1 != 0 else 0.0

            is_harvest  = 1 if month in [10,11,12] else 0
            is_lean     = 1 if month in [6,7,8]    else 0

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
                "month_sin":            math.sin(2*math.pi*month/12),
                "month_cos":            math.cos(2*math.pi*month/12),
                "is_harvest_season":    is_harvest,
                "is_lean_season":       is_lean,
                "price_vs_annual":      price_vs_ann,
                "price_yoy":            price_yoy,
            }
            feat_df    = pd.DataFrame([feat_row])
            result     = predict_decision(feat_df)
            ml_decision   = result["decision"]
            ml_confidence = result["confidence"]
            ml_all_probs  = result["all_probs"]
            ml_model_used = result["model_used"]

        except Exception as e:
            print(f"[ml_service] Classifier prediction failed, using fallback: {e}")

    # Use ML decision if available, otherwise use rule-based from calculate_net_return
    final_decision = ml_decision if ml_decision else decision_data["decision"]

    #  Storage 
    storage = storage_service.get_nearest_storage(
        district=district, crop=crop, db=db
    )

    # Log recommendation to MySQL 
    if db and phone_number:
        try:
            rec = Recommendation(
                session_id   = session_id,
                phone_number = phone_number,
                language     = language,
                crop         = crop,
                district     = district,
                quantity_bags= quantity_bags,
                current_price= current_price,
                forecast_price=forecast_price,
                decision     = final_decision,
                net_return   = decision_data["net_total"],
                storage_id   = None,
            )
            db.add(rec)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[ml_service] Failed to log recommendation: {e}")

    
    return {
        
        "decision":       final_decision,
        "current_price":  current_price,
        "forecast_price": forecast_price,
        "expected_gain":  decision_data["expected_gain"],
        "net_per_bag":    decision_data["net_per_bag"],
        "net_total":      decision_data["net_total"],
        "crop":           crop,
        "district":       district,
        "storage":        storage[0] if storage else None,
        "method":         forecast_data.get("method"),
        "ml_confidence":  ml_confidence,
        "ml_all_probs":   ml_all_probs,
        "ml_model_used":  ml_model_used,
    }