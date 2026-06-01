"""
app/ml/train_lstm.py

Retraining script for the multivariate LSTM price forecaster.
Pulls price data from MySQL and retrains the LSTM from scratch.

Run from the project root:
    python -m app.ml.train_lstm
"""

import json
import numpy as np
import pandas as pd
import joblib
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.core.database import engine
from app.ml.config import (
    LSTM_PATH, LSTM_SCALER_PATH, PRICE_SCALER_PATH, METADATA_PATH,
    LSTM_FEAT_COLS, LSTM_SEQ_LEN, LSTM_HIDDEN, LSTM_LAYERS, LSTM_DROPOUT,
)

SEED     = 42
DEVICE   = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
EPOCHS   = 100
BATCH    = 32
LR       = 0.001
PATIENCE = 15
TRAIN_R, VAL_R = 0.70, 0.15

torch.manual_seed(SEED)
np.random.seed(SEED)


class MultivariateLSTM(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        self.lstm = nn.LSTM(input_size, LSTM_HIDDEN, LSTM_LAYERS,
                            batch_first=True, dropout=LSTM_DROPOUT)
        self.fc   = nn.Linear(LSTM_HIDDEN, 1)

    def forward(self, x):
        h0 = torch.zeros(LSTM_LAYERS, x.size(0), LSTM_HIDDEN).to(DEVICE)
        c0 = torch.zeros(LSTM_LAYERS, x.size(0), LSTM_HIDDEN).to(DEVICE)
        out, _ = self.lstm(x, (h0, c0))
        return self.fc(out[:, -1, :])


def make_sequences(data, seq_len):
    X, y = [], []
    for i in range(len(data) - seq_len):
        X.append(data[i:i+seq_len, :])
        y.append(data[i+seq_len, 0:1])
    return np.array(X), np.array(y)


def retrain():
    print(f"Device: {DEVICE}")

    query = """
        SELECT
            p.date,
            AVG(p.price)     AS price,
            AVG(fx.value)    AS exchange_rate,
            AVG(pp.value)    AS producer_price_index,
            SIN(2*PI()*MONTH(p.date)/12) AS month_sin,
            COS(2*PI()*MONTH(p.date)/12) AS month_cos
        FROM wfp_prices p
        LEFT JOIN ghana_exchange_rates fx
            ON fx.year=YEAR(p.date) AND fx.months=DATE_FORMAT(p.date,'%M')
            AND fx.element='Local currency units per USD'
        LEFT JOIN fao_producer_prices pp
            ON pp.year=YEAR(p.date) AND pp.months='Annual value'
            AND pp.element='Producer Price Index (2014-2016 = 100)'
        WHERE p.commodity IN ('Maize','Millet','Sorghum')
          AND p.pricetype='Wholesale'
          AND p.market IN ('Tamale','Bolga','Wa','Kumasi','Techiman')
        GROUP BY p.date
        ORDER BY p.date
    """
    df = pd.read_sql(query, engine)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').dropna().reset_index(drop=True)

    # Add lag features for multivariate input
    df['price_lag1']     = df['price'].shift(1)
    df['price_lag2']     = df['price'].shift(2)
    df['price_lag3']     = df['price'].shift(3)
    df['rolling_mean_3'] = df['price'].rolling(3, min_periods=1).mean()
    df['rolling_std_3']  = df['price'].rolling(3, min_periods=2).std()
    df = df.dropna().reset_index(drop=True)

    print(f"Time series rows: {len(df)}")

    n = len(df); n_tr = int(n*TRAIN_R); n_va = int(n*VAL_R)
    ts_tr = df.iloc[:n_tr]; ts_va = df.iloc[n_tr:n_tr+n_va]; ts_te = df.iloc[n_tr+n_va:]

    scaler  = MinMaxScaler()
    p_sc    = MinMaxScaler()
    tr_sc   = scaler.fit_transform(ts_tr[LSTM_FEAT_COLS].values)
    va_sc   = scaler.transform(ts_va[LSTM_FEAT_COLS].values)
    te_sc   = scaler.transform(ts_te[LSTM_FEAT_COLS].values)
    p_sc.fit(ts_tr[['price']].values)

    Xtr, ytr = make_sequences(tr_sc, LSTM_SEQ_LEN)
    Xva, yva = make_sequences(va_sc, LSTM_SEQ_LEN)
    Xte, yte = make_sequences(te_sc, LSTM_SEQ_LEN)

    def to_t(a): return torch.FloatTensor(a).to(DEVICE)
    train_dl = DataLoader(TensorDataset(to_t(Xtr), to_t(ytr)), batch_size=BATCH, shuffle=False)
    val_dl   = DataLoader(TensorDataset(to_t(Xva), to_t(yva)), batch_size=BATCH, shuffle=False)

    model     = MultivariateLSTM(len(LSTM_FEAT_COLS)).to(DEVICE)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    best_val, patience_count = float('inf'), 0
    checkpoint = LSTM_PATH.replace('.pt', '_checkpoint.pt')

    print(f"Training (max {EPOCHS} epochs, patience={PATIENCE}) ...")
    for epoch in range(EPOCHS):
        model.train()
        ep_loss = 0
        for xb, yb in train_dl:
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            ep_loss += loss.item()
        avg_tr = ep_loss / len(train_dl)

        model.eval()
        with torch.no_grad():
            avg_va = sum(criterion(model(xb), yb).item() for xb,yb in val_dl) / len(val_dl)

        scheduler.step(avg_va)
        if avg_va < best_val:
            best_val, patience_count = avg_va, 0
            torch.save(model.state_dict(), checkpoint)
        else:
            patience_count += 1

        if (epoch+1) % 10 == 0:
            print(f"  Epoch {epoch+1:3d}  train={avg_tr:.5f}  val={avg_va:.5f}  pat={patience_count}/{PATIENCE}")
        if patience_count >= PATIENCE:
            print(f"  Early stop at epoch {epoch+1}.")
            break

    model.load_state_dict(torch.load(checkpoint, map_location=DEVICE))
    torch.save(model.state_dict(), LSTM_PATH)

    # Evaluate
    model.eval()
    with torch.no_grad():
        preds_sc = model(to_t(Xte)).cpu().numpy()
    preds = p_sc.inverse_transform(preds_sc).flatten()
    true  = p_sc.inverse_transform(yte.reshape(-1,1)).flatten()

    mae  = mean_absolute_error(true, preds)
    rmse = float(np.sqrt(mean_squared_error(true, preds)))
    r2   = r2_score(true, preds)
    print(f"\nLSTM Test — MAE={mae:.2f}  RMSE={rmse:.2f}  R²={r2:.4f}")

    joblib.dump(scaler, LSTM_SCALER_PATH)
    joblib.dump(p_sc,   PRICE_SCALER_PATH)

    try:
        with open(METADATA_PATH) as f:
            metadata = json.load(f)
    except FileNotFoundError:
        metadata = {}

    metadata.update({
        'lstm_seq_len': LSTM_SEQ_LEN,
        'lstm_hidden':  LSTM_HIDDEN,
        'lstm_layers':  LSTM_LAYERS,
        'lstm_features':LSTM_FEAT_COLS,
        'lstm_mae_ghs': round(mae, 2),
        'lstm_rmse_ghs':round(rmse, 2),
        'lstm_r2':      round(r2, 4),
    })
    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)

    print("LSTM artifacts saved ")


if __name__ == "__main__":
    retrain()