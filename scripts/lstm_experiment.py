# Run: python -m scripts.lstm_experiment
#
# Experiment: can the LSTM win the forecaster competition when trained the way
# LSTMs need — one global model across all 15 market-crop series (5x more
# sequences) with a network sized to the data?
#
# All contenders see identical features, identical per-series chronological
# splits, and identical 3-month-ahead targets. Does NOT touch production
# artifacts — results are printed for comparison only.

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sqlalchemy import text
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import xgboost as xgb

from app.core.database import engine
from app.ml.config import (
    TRAIN_START, VALID_MARKETS, VALID_COMMODITIES, FORECAST_HORIZON_MONTHS,
    LSTM_SEQ_LEN,
)

SEED = 42
TRAIN_R, VAL_R = 0.70, 0.15
EPOCHS, BATCH, LR, PATIENCE = 100, 32, 0.001, 15

torch.manual_seed(SEED)
np.random.seed(SEED)

FEATS = (
    ['price', 'exchange_rate', 'month_sin', 'month_cos',
     'price_lag1', 'price_lag2', 'price_lag3', 'rolling_mean_3', 'rolling_std_3']
    + [f'crop_{c}' for c in VALID_COMMODITIES]
    + [f'mkt_{m}' for m in VALID_MARKETS]
)


class LSTMReg(nn.Module):
    def __init__(self, input_size, hidden, layers, drop=0.2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden, layers, batch_first=True,
                            dropout=drop if layers > 1 else 0.0)
        self.fc = nn.Linear(hidden, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


def load_market_series() -> pd.DataFrame:
    query = """
        SELECT
            p.market, p.commodity, p.date,
            AVG(p.price)  AS price,
            AVG(fx.value) AS exchange_rate,
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
    return df.dropna().reset_index(drop=True)


def split_series(df):
    tr, va, te = [], [], []
    for _, g in df.groupby(['market', 'commodity']):
        n = len(g); n_tr = int(n*TRAIN_R); n_va = int(n*VAL_R)
        tr.append(g.iloc[:n_tr])
        va.append(g.iloc[n_tr:n_tr+n_va])
        te.append(g.iloc[n_tr+n_va:])
    return tr, va, te


def make_seq(feats, target, seq_len):
    """Window ends at t; 'target' column already holds the t+3 value."""
    X, y = [], []
    for i in range(len(feats) - seq_len + 1):
        X.append(feats[i:i+seq_len])
        y.append(target[i+seq_len-1])
    return np.array(X), np.array(y).reshape(-1, 1)


def eval_metrics(per_series_preds):
    preds = np.concatenate([p for p, _ in per_series_preds])
    true  = np.concatenate([t for _, t in per_series_preds])
    dirs  = np.concatenate([
        np.sign(p[1:]-p[:-1]) == np.sign(t[1:]-t[:-1])
        for p, t in per_series_preds if len(p) > 1
    ])
    return {
        'MAE':    round(float(mean_absolute_error(true, preds)), 2),
        'R2':     round(float(r2_score(true, preds)), 4),
        'DirAcc': round(float(np.mean(dirs)) * 100, 1),
        'n_test': len(true),
    }


def run_lstm_variant(name, hidden, layers, tr_parts, va_parts, te_parts, scaler, t_sc):
    torch.manual_seed(SEED)

    def stack(parts):
        X, y = [], []
        for g in parts:
            f = scaler.transform(g[FEATS].values)
            t = t_sc.transform(g[['target']].values).flatten()
            Xg, yg = make_seq(f, t, LSTM_SEQ_LEN)
            if len(Xg):
                X.append(Xg); y.append(yg)
        return np.concatenate(X), np.concatenate(y)

    Xtr, ytr = stack(tr_parts)
    Xva, yva = stack(va_parts)

    def _t(a): return torch.FloatTensor(a)
    train_dl = DataLoader(TensorDataset(_t(Xtr), _t(ytr)), batch_size=BATCH, shuffle=False)
    val_dl   = DataLoader(TensorDataset(_t(Xva), _t(yva)), batch_size=BATCH, shuffle=False)

    model     = LSTMReg(len(FEATS), hidden, layers)
    n_params  = sum(p.numel() for p in model.parameters())
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    best_val, pat, best_state = float('inf'), 0, None
    for epoch in range(EPOCHS):
        model.train()
        for xb, yb in train_dl:
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        model.eval()
        with torch.no_grad():
            avg_va = sum(criterion(model(xb), yb).item() for xb, yb in val_dl) / len(val_dl)
        scheduler.step(avg_va)
        if avg_va < best_val:
            best_val, pat = avg_va, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            pat += 1
        if pat >= PATIENCE:
            break

    model.load_state_dict(best_state)
    model.eval()

    per_series = []
    for g in te_parts:
        f = scaler.transform(g[FEATS].values)
        t = t_sc.transform(g[['target']].values).flatten()
        Xte, yte = make_seq(f, t, LSTM_SEQ_LEN)
        if not len(Xte):
            continue
        with torch.no_grad():
            preds_sc = model(_t(Xte)).numpy()
        preds = np.exp(t_sc.inverse_transform(preds_sc).flatten())
        true  = np.exp(t_sc.inverse_transform(yte).flatten())
        per_series.append((preds, true))

    m = eval_metrics(per_series)
    m['params'] = n_params
    return name, m


def run_sarima(tr_parts, va_parts, te_parts):
    """SARIMA per-series: fit on train+val log-prices, 3-month-ahead forecast."""
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
    except ImportError:
        print("  statsmodels not installed — skipping SARIMA")
        return None

    per_series, failed = [], 0
    for tr, va, te in zip(tr_parts, va_parts, te_parts):
        if len(te) < 4:
            continue
        try:
            tr_va  = pd.concat([tr, va])['price'].values   # log prices
            te_tgt = te['target'].values                    # log prices t+3
            n_te   = len(te_tgt)

            model  = SARIMAX(tr_va, order=(1, 1, 1),
                             seasonal_order=(1, 1, 1, 12),
                             enforce_stationarity=False,
                             enforce_invertibility=False)
            fitted = model.fit(disp=False, maxiter=100)

            # step k (1-indexed) from end of train+val = price at T+k
            # test row i target = T + (i+1) + 3 = step i+4, 0-indexed: [i+3]
            n_steps = FORECAST_HORIZON_MONTHS + n_te
            fcast   = fitted.forecast(steps=n_steps)
            preds   = np.exp(fcast[FORECAST_HORIZON_MONTHS: FORECAST_HORIZON_MONTHS + n_te])
            true    = np.exp(te_tgt)
            per_series.append((preds, true))
        except Exception:
            failed += 1

    if failed:
        print(f"  SARIMA: {failed} series failed, skipped")
    if not per_series:
        return None
    return eval_metrics(per_series)


def run():
    df = load_market_series()
    n_series = df.groupby(['market', 'commodity']).ngroups
    print(f"Market-level rows: {len(df)}  ({n_series} series)")

    tr_parts, va_parts, te_parts = split_series(df)
    tr_all = pd.concat(tr_parts)

    scaler = MinMaxScaler().fit(tr_all[FEATS].values)
    t_sc   = MinMaxScaler().fit(tr_all[['target']].values)

    results = {}

    for name, hidden, layers in [
        ('LSTM 2x64 (current size)', 64, 2),
        ('LSTM 1x24',                24, 1),
        ('LSTM 1x16',                16, 1),
    ]:
        n, m = run_lstm_variant(name, hidden, layers, tr_parts, va_parts, te_parts, scaler, t_sc)
        results[n] = m
        print(f"  trained {n}  ({m['params']:,} params)")

    # flat baselines: same features at window-end time t, same targets
    trva = pd.concat(tr_parts + va_parts)
    flat_models = {
        'RF Regressor':  RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=-1),
        'XGB Regressor': xgb.XGBRegressor(n_estimators=300, max_depth=4,
                                          learning_rate=0.05, random_state=SEED),
    }
    for name, model in flat_models.items():
        model.fit(trva[FEATS].values, trva['target'].values)
        per_series = []
        for g in te_parts:
            ge = g.iloc[LSTM_SEQ_LEN-1:]          # align with LSTM-predictable rows
            if not len(ge):
                continue
            preds = np.exp(model.predict(ge[FEATS].values))
            true  = np.exp(ge['target'].values)
            per_series.append((preds, true))
        results[name] = eval_metrics(per_series)

    per_series = []
    for g in te_parts:
        ge = g.iloc[LSTM_SEQ_LEN-1:]
        if not len(ge):
            continue
        per_series.append((np.exp(ge['price'].values), np.exp(ge['target'].values)))
    results['Naive (no change)'] = eval_metrics(per_series)

    print("  fitting SARIMA(1,1,1)(1,1,1,12) per series (~60s) ...")
    sarima = run_sarima(tr_parts, va_parts, te_parts)
    if sarima:
        results['SARIMA(1,1,1)x(1,1,1,12)'] = sarima

    print(f"\n{'Model':<30} {'MAE':>8} {'R²':>9} {'DirAcc':>8} {'params':>9}")
    print('-' * 68)
    for name, m in sorted(results.items(), key=lambda kv: kv[1]['MAE']):
        p = f"{m.get('params', 0):,}" if m.get('params') else '—'
        print(f"{name:<30} {m['MAE']:>8.2f} {m['R2']:>9.4f} {m['DirAcc']:>7.1f}% {p:>9}")
    print(f"\n(test points: {results['Naive (no change)']['n_test']}, "
          f"task: {FORECAST_HORIZON_MONTHS}-month-ahead, 15 market-crop series)")


if __name__ == "__main__":
    run()
