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
    """Returns the forecast price FORECAST_HORIZON_MONTHS (3) months ahead,
    matching the storage decision horizon."""
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
