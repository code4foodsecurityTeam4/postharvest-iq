"""
Inference module. All model artifacts are loaded once at import time and held in
module-level variables to avoid repeated disk I/O on every API request.

Log-space inversion
    The LSTM was trained to predict log(price). Its raw output is in the
    MinMaxScaler's [0,1] range over log prices. Recovering the GHS price:
        1. price_scaler.inverse_transform(raw_output)  →  log(price)
        2. np.exp(log_price)                           →  GHS price
    Both steps require the exact price_scaler instance saved during training.
    Using a freshly-fit scaler here would silently produce wrong prices.

Classifier pipeline
    The ColumnTransformer (ohe + passthrough) and LabelEncoder are both saved
    artifacts. The preprocessor must receive columns in the same order it was
    fit on — [CAT_COLS + NUM_COLS] — or OneHotEncoder will silently mismap categories.
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


class MultivariateLSTM(nn.Module):
    """
    Inference-only copy of the training architecture. Must be structurally
    identical to the definition in train_lstm.py so load_state_dict() succeeds.

    h0/c0 are zero-initialised per call. The model is stateless across requests.
    """

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


def forecast_price(recent_feature_df: pd.DataFrame) -> float:
    """
    Forecast the wholesale price 3 months ahead for a specific market-crop series.

    Args:
        recent_feature_df: DataFrame with at least LSTM_SEQ_LEN rows. Must contain
                           all columns in LSTM_FEAT_COLS in the correct order.
                           The 'price' column must be log-transformed — it is
                           log-transformed in _get_lstm_sequence() before this call.

    Returns:
        Forecast price in GHS, rounded to 2 decimal places.

    Raises:
        ValueError: if fewer than LSTM_SEQ_LEN rows are provided.
    """
    if len(recent_feature_df) < LSTM_SEQ_LEN:
        raise ValueError(
            f"Need at least {LSTM_SEQ_LEN} monthly rows, got {len(recent_feature_df)}."
        )

    seq       = recent_feature_df[LSTM_FEAT_COLS].values[-LSTM_SEQ_LEN:]
    scaled    = _lstm_scaler.transform(seq)
    tensor    = torch.FloatTensor(scaled).unsqueeze(0)

    with torch.no_grad():
        pred_scaled = _lstm(tensor).numpy()

    # model works in log space; exp back to GHS
    pred_price = np.exp(_price_scaler.inverse_transform(pred_scaled)[0, 0])
    return round(float(pred_price), 2)


def predict_decision(input_df: pd.DataFrame) -> dict:
    """
    Run the trained classifier on a single feature row.

    Args:
        input_df: single-row DataFrame with 'market', 'commodity', and all NUM_COLS.
                  Prices should be in raw GHS — the classifier was trained on
                  raw (not log-transformed) prices, unlike the LSTM.

    Returns:
        dict with:
            decision    ('STORE' or 'SELL_NOW')
            confidence  (probability of the predicted class, float 0–1)
            model_used  (algorithm name from metadata)
            all_probs   (dict of class → probability for all classes)
    """
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
    return _metadata
