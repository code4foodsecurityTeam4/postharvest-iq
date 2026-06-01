"""
app/ml/predict.py

Public interface for all ML predictions.
Called by app/services/ml_service.py — never called directly from routes.

Two public functions:
    forecast_price(recent_prices, recent_features) → float
    predict_decision(input_df)                     → dict
"""

import json
import numpy as np
import pandas as pd
import joblib
import torch
import torch.nn as nn

from app.ml.config import (
    CLASSIFIER_PATH, PREPROCESSING_PIPELINE_PATH, LABEL_ENCODER_PATH,
    FEATURE_COLUMNS_PATH, LSTM_PATH, LSTM_SCALER_PATH, PRICE_SCALER_PATH,
    METADATA_PATH, LSTM_FEAT_COLS,
    LSTM_SEQ_LEN, LSTM_HIDDEN, LSTM_LAYERS, LSTM_DROPOUT,
)


#  LSTM definition  
class MultivariateLSTM(nn.Module):
    def __init__(self, input_size, hidden=LSTM_HIDDEN,
                 layers=LSTM_LAYERS, drop=LSTM_DROPOUT):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden, layers,
                            batch_first=True, dropout=drop)
        self.fc   = nn.Linear(hidden, 1)

    def forward(self, x):
        h0 = torch.zeros(LSTM_LAYERS, x.size(0), LSTM_HIDDEN)
        c0 = torch.zeros(LSTM_LAYERS, x.size(0), LSTM_HIDDEN)
        out, _ = self.lstm(x, (h0, c0))
        return self.fc(out[:, -1, :])


#  Load all models once at import time 
# Models are loaded when FastAPI starts — not on every request.

_classifier    = joblib.load(CLASSIFIER_PATH)
_preprocessor  = joblib.load(PREPROCESSING_PIPELINE_PATH)
_label_encoder = joblib.load(LABEL_ENCODER_PATH)
_feature_cols  = joblib.load(FEATURE_COLUMNS_PATH)
_lstm_scaler   = joblib.load(LSTM_SCALER_PATH)
_price_scaler  = joblib.load(PRICE_SCALER_PATH)

_n_lstm_feat = len(LSTM_FEAT_COLS)
_lstm = MultivariateLSTM(_n_lstm_feat)
_lstm.load_state_dict(torch.load(LSTM_PATH, map_location='cpu'))
_lstm.eval()

with open(METADATA_PATH) as f:
    _metadata = json.load(f)


#  Public functions 

def forecast_price(recent_feature_df: pd.DataFrame) -> float:
    """
    Forecast next month's price using the multivariate LSTM.

    Args:
        recent_feature_df : DataFrame with at least SEQ_LEN (12) rows,
                            containing columns: price, exchange_rate,
                            producer_price_index, month_sin, month_cos,
                            price_lag1, price_lag2, price_lag3,
                            rolling_mean_3, rolling_std_3.
                            Rows must be sorted oldest → newest.

    Returns:
        Predicted price for next month (GHS/100kg) as a float.

    Raises:
        ValueError: if fewer than SEQ_LEN rows are provided.
    """
    if len(recent_feature_df) < LSTM_SEQ_LEN:
        raise ValueError(
            f"Need at least {LSTM_SEQ_LEN} monthly rows, got {len(recent_feature_df)}."
        )

    seq       = recent_feature_df[LSTM_FEAT_COLS].values[-LSTM_SEQ_LEN:]
    scaled    = _lstm_scaler.transform(seq)
    tensor    = torch.FloatTensor(scaled).unsqueeze(0)  # (1, 12, features)

    with torch.no_grad():
        pred_scaled = _lstm(tensor).numpy()

    # The scaler covers all LSTM features — inverse-transform price column only
    dummy        = np.zeros((1, _n_lstm_feat))
    dummy[0, 0]  = pred_scaled[0, 0]
    pred_price   = _lstm_scaler.inverse_transform(dummy)[0, 0]
    return round(float(pred_price), 2)


def predict_decision(input_df: pd.DataFrame) -> dict:
    """
    Predict the sell/store decision using the trained classifier.

    Args:
        input_df : Single-row DataFrame with these columns:
                    market, commodity,
                    price_lag1, price_lag2, price_lag3,
                    rolling_mean_3, rolling_std_3, price_pct_change,
                    exchange_rate, producer_price_index,
                    month_sin, month_cos,
                    is_harvest_season, is_lean_season,
                    price_vs_annual, price_yoy

    Returns:
        {
            'decision'   : 'STORE' | 'SELL_NOW' | 'SELL_PARTIAL',
            'confidence' : float 0-1,
            'model_used' : str,
            'all_probs'  : {class_name: probability}
        }
    """
    # Use the fitted ColumnTransformer to encode market/commodity
    # and pass through numerical features in the exact order seen during training
    CAT_COLS = ['market', 'commodity']
    NUM_COLS = [c for c in _feature_cols if c not in
                _preprocessor.named_transformers_['ohe']
                .get_feature_names_out(CAT_COLS).tolist()]

    X = _preprocessor.transform(input_df[CAT_COLS + NUM_COLS])

    pred_encoded = _classifier.predict(X)[0]
    pred_proba   = _classifier.predict_proba(X)[0]
    decision     = _label_encoder.inverse_transform([pred_encoded])[0]
    confidence   = round(float(pred_proba.max()), 4)

    all_probs = {
        cls: round(float(prob), 4)
        for cls, prob in zip(_label_encoder.classes_, pred_proba)
    }

    return {
        'decision':   decision,
        'confidence': confidence,
        'model_used': _metadata.get('best_classifier', 'unknown'),
        'all_probs':  all_probs,
    }


def get_model_info() -> dict:
    """Returns training metadata for the /forecasts/model-info endpoint."""
    return _metadata