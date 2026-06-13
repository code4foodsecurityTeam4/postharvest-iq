# Run: python -m app.ml.train_lstm

import json
import numpy as np
import pandas as pd
import joblib
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sqlalchemy import text

from app.core.database import engine
from app.ml.config import (
    LSTM_PATH, LSTM_SCALER_PATH, PRICE_SCALER_PATH, METADATA_PATH,
    LSTM_FEAT_COLS, LSTM_SEQ_LEN, LSTM_HIDDEN, LSTM_LAYERS, LSTM_DROPOUT,
    TRAIN_START, VALID_COMMODITIES, VALID_MARKETS, FORECAST_HORIZON_MONTHS,
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


def make_sequences(feats, target, seq_len):
    """Direct multi-step: each window targets the price FORECAST_HORIZON_MONTHS ahead, not recursive."""
    X, y = [], []
    for i in range(len(feats) - seq_len + 1):
        X.append(feats[i:i+seq_len])
        y.append(target[i+seq_len-1])
    return np.array(X), np.array(y).reshape(-1, 1)


def retrain():
    print(f"Device: {DEVICE}")

    query = """
        SELECT
            p.market,
            p.commodity,
            p.date,
            AVG(p.price)     AS price,
            AVG(fx.value)    AS exchange_rate,
            SIN(2*PI()*MONTH(p.date)/12) AS month_sin,
            COS(2*PI()*MONTH(p.date)/12) AS month_cos
        FROM wfp_prices p
        LEFT JOIN ghana_exchange_rates fx
            ON fx.year=YEAR(p.date) AND fx.months=DATE_FORMAT(p.date,'%M')
            AND fx.element='Local currency units per USD'
        WHERE p.commodity IN ('Maize','Millet','Sorghum')
          AND p.pricetype='Wholesale'
          AND p.market IN ('Tamale','Bolga','Wa','Kumasi','Techiman')
          AND p.date >= '{TRAIN_START}'
        GROUP BY p.market, p.commodity, p.date
        ORDER BY p.market, p.commodity, p.date
    """.format(TRAIN_START=TRAIN_START)
    df = pd.read_sql(text(query), engine)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['market', 'commodity', 'date']).dropna().reset_index(drop=True)

    # model in log space; lags/rolling stats are derived from the logged series
    df['price'] = np.log(df['price'])

    grp = df.groupby(['market', 'commodity'])['price']
    df['price_lag1']     = grp.shift(1)
    df['price_lag2']     = grp.shift(2)
    df['price_lag3']     = grp.shift(3)
    df['rolling_mean_3'] = grp.transform(lambda x: x.rolling(3, min_periods=1).mean())
    df['rolling_std_3']  = grp.transform(lambda x: x.rolling(3, min_periods=2).std())
    df['target']         = grp.shift(-FORECAST_HORIZON_MONTHS)
    for c in VALID_COMMODITIES:
        df[f'crop_{c}'] = (df['commodity'] == c).astype(float)
    for m in VALID_MARKETS:
        df[f'mkt_{m}'] = (df['market'] == m).astype(float)
    df = df.dropna().reset_index(drop=True)

    n_series = df.groupby(['market', 'commodity']).ngroups
    print(f"Time series rows: {len(df)} ({n_series} market-crop series)")

    tr_parts, va_parts, te_parts = [], [], []
    for _, gdf in df.groupby(['market', 'commodity']):
        n = len(gdf); n_tr = int(n*TRAIN_R); n_va = int(n*VAL_R)
        tr_parts.append(gdf.iloc[:n_tr])
        va_parts.append(gdf.iloc[n_tr:n_tr+n_va])
        te_parts.append(gdf.iloc[n_tr+n_va:])

    scaler = MinMaxScaler()
    p_sc   = MinMaxScaler()
    scaler.fit(pd.concat(tr_parts)[LSTM_FEAT_COLS].values)
    p_sc.fit(pd.concat(tr_parts)[['target']].values)

    def stack_sequences(parts):
        X, y = [], []
        for gdf in parts:
            feats  = scaler.transform(gdf[LSTM_FEAT_COLS].values)
            target = p_sc.transform(gdf[['target']].values).flatten()
            Xg, yg = make_sequences(feats, target, LSTM_SEQ_LEN)
            if len(Xg):
                X.append(Xg)
                y.append(yg)
        return np.concatenate(X), np.concatenate(y)

    Xtr, ytr = stack_sequences(tr_parts)
    Xva, yva = stack_sequences(va_parts)
    print(f"Sequences — train: {len(Xtr)}  val: {len(Xva)}")

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
            avg_va = sum(criterion(model(xb), yb).item() for xb, yb in val_dl) / len(val_dl)

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

    model.eval()
    crop_acc = {c: {'preds': [], 'true': [], 'dirs': []} for c in VALID_COMMODITIES}
    for gdf in te_parts:
        crop   = gdf['commodity'].iloc[0]
        feats  = scaler.transform(gdf[LSTM_FEAT_COLS].values)
        target = p_sc.transform(gdf[['target']].values).flatten()
        Xte, yte = make_sequences(feats, target, LSTM_SEQ_LEN)
        if not len(Xte):
            continue
        with torch.no_grad():
            preds_sc = model(to_t(Xte)).cpu().numpy()
        preds = np.exp(p_sc.inverse_transform(preds_sc).flatten())
        true  = np.exp(p_sc.inverse_transform(yte).flatten())
        crop_acc[crop]['preds'].append(preds)
        crop_acc[crop]['true'].append(true)
        crop_acc[crop]['dirs'].append(
            np.sign(preds[1:] - preds[:-1]) == np.sign(true[1:] - true[:-1]))

    per_crop = {}
    for crop, acc in crop_acc.items():
        if not acc['preds']:
            continue
        c_preds = np.concatenate(acc['preds'])
        c_true  = np.concatenate(acc['true'])
        per_crop[crop] = {
            'mae':     round(float(mean_absolute_error(c_true, c_preds)), 2),
            'dir_acc': round(float(np.mean(np.concatenate(acc['dirs']))) * 100, 1),
        }
        print(f"  {crop:<8} test MAE={per_crop[crop]['mae']:.2f}  DirAcc={per_crop[crop]['dir_acc']:.1f}%")

    all_dirs = [d for acc in crop_acc.values() for d in acc['dirs']]
    preds = np.concatenate([p for acc in crop_acc.values() for p in acc['preds']])
    true  = np.concatenate([t for acc in crop_acc.values() for t in acc['true']])

    mae     = mean_absolute_error(true, preds)
    rmse    = float(np.sqrt(mean_squared_error(true, preds)))
    r2      = r2_score(true, preds)
    dir_acc = float(np.mean(np.concatenate(all_dirs))) * 100
    print(f"\nLSTM Test — MAE={mae:.2f}  RMSE={rmse:.2f}  R²={r2:.4f}  DirAcc={dir_acc:.1f}%")

    joblib.dump(scaler, LSTM_SCALER_PATH)
    joblib.dump(p_sc,   PRICE_SCALER_PATH)

    try:
        with open(METADATA_PATH) as f:
            metadata = json.load(f)
    except FileNotFoundError:
        metadata = {}

    metadata.update({
        'lstm_seq_len':      LSTM_SEQ_LEN,
        'lstm_hidden':       LSTM_HIDDEN,
        'lstm_layers':       LSTM_LAYERS,
        'lstm_features':     LSTM_FEAT_COLS,
        'lstm_target':       'log_price_per_market_crop',
        'lstm_train_start':  TRAIN_START,
        'lstm_mae_ghs':      round(mae, 2),
        'lstm_rmse_ghs':     round(rmse, 2),
        'lstm_r2':           round(r2, 4),
        'lstm_dir_accuracy': round(dir_acc, 1),
        'lstm_per_crop':     per_crop,
    })
    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)

    print("LSTM artifacts saved ")


if __name__ == "__main__":
    retrain()
