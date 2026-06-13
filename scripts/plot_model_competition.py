# Run: python -m scripts.plot_model_competition
#
# Generates the model-competition chart: which classifier won the decision
# tournament, and how the LSTM compares against tree-ensemble regressors on
# the same per-crop, 3-month-ahead forecasting task.
#
# Classifier standings are read from model_metadata.json (written by
# train_xgboost). Forecaster baselines are trained here on identical data so
# the comparison is apples-to-apples, then saved back to the metadata.

import os
import sys
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb

from app.ml.config import (
    METADATA_PATH, MODELS_DIR, LSTM_SEQ_LEN, FORECAST_HORIZON_MONTHS,
)
from scripts.lstm_experiment import (
    load_market_series, split_series, eval_metrics, run_sarima, FEATS,
)

SEED = 42
OUT_PATH = os.path.join(MODELS_DIR, "model_competition.png")


def run_forecaster_baselines() -> dict:
    """Flat-feature regressors and naive baseline on the production LSTM's
    exact task: 15 market-crop series, 3-month-ahead, identical features."""
    df = load_market_series()
    tr_parts, va_parts, te_parts = split_series(df)
    trva = pd.concat(tr_parts + va_parts)

    models = {
        'RF Regressor':  RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=-1),
        'XGB Regressor': xgb.XGBRegressor(n_estimators=300, max_depth=4,
                                          learning_rate=0.05, random_state=SEED),
    }

    out = {}
    for name, model in models.items():
        model.fit(trva[FEATS].values, trva['target'].values)
        per_series = []
        for g in te_parts:
            ge = g.iloc[LSTM_SEQ_LEN-1:]       # align with LSTM-predictable rows
            if not len(ge):
                continue
            per_series.append((np.exp(model.predict(ge[FEATS].values)),
                               np.exp(ge['target'].values)))
        out[name] = eval_metrics(per_series)

    per_series = []
    for g in te_parts:
        ge = g.iloc[LSTM_SEQ_LEN-1:]
        if not len(ge):
            continue
        per_series.append((np.exp(ge['price'].values), np.exp(ge['target'].values)))
    out['Naive (no change)'] = eval_metrics(per_series)

    print("  fitting SARIMA(1,1,1)(1,1,1,12) per series (~60s) ...")
    sarima = run_sarima(tr_parts, va_parts, te_parts)
    if sarima:
        out['SARIMA(1,1,1)x(1,1,1,12)'] = sarima

    return out


def run():
    with open(METADATA_PATH) as f:
        meta = json.load(f)

    cls_results = meta['all_cls_results']
    best_cls    = meta['best_classifier']

    print("Training forecaster baselines on the LSTM's task...")
    fc_results = run_forecaster_baselines()
    fc_results['LSTM'] = {
        'MAE':    meta['lstm_mae_ghs'],
        'R2':     meta['lstm_r2'],
        'DirAcc': meta['lstm_dir_accuracy'],
    }

    meta['all_forecast_results'] = fc_results
    with open(METADATA_PATH, 'w') as f:
        json.dump(meta, f, indent=2)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))
    fig.suptitle(
        f'Model competition — decision classifier and {FORECAST_HORIZON_MONTHS}-month price forecaster',
        fontsize=14, fontweight='bold',
    )

    # panel 1: classifier tournament
    ax = axes[0]
    names = sorted(cls_results, key=lambda k: cls_results[k]['val_f1'])
    val   = [cls_results[n]['val_f1'] for n in names]
    tst   = [cls_results[n]['test_f1'] for n in names]
    ypos  = np.arange(len(names))
    ax.barh(ypos + 0.2, val, height=0.38, label='Validation F1',
            color=['#2a9d8f' if n == best_cls else '#a8c5c1' for n in names])
    ax.barh(ypos - 0.2, tst, height=0.38, label='Test F1',
            color=['#1d6e64' if n == best_cls else '#cdddda' for n in names])
    ax.set_yticks(ypos)
    ax.set_yticklabels([f'{n} ◀ selected' if n == best_cls else n for n in names])
    ax.set_xlabel('Macro F1 (higher is better)')
    ax.set_title('Decision classifier tournament\n(selected on validation F1)')
    ax.set_xlim(0, 1)
    ax.legend(loc='lower right', fontsize=9)
    ax.grid(axis='x', alpha=0.3)

    # panel 2: forecaster MAE
    ax = axes[1]
    fnames = sorted(fc_results, key=lambda k: -fc_results[k]['MAE'])
    mae    = [fc_results[n]['MAE'] for n in fnames]
    colors = ['#e76f51' if n == 'LSTM' else '#e9c4ba' for n in fnames]
    ax.barh(np.arange(len(fnames)), mae, color=colors)
    ax.set_yticks(np.arange(len(fnames)))
    ax.set_yticklabels([f'{n} ◀ selected' if n == 'LSTM' else n for n in fnames])
    ax.set_xlabel('Test MAE in GHS (lower is better)')
    ax.set_title('Forecaster — error in cedis')
    for i, v in enumerate(mae):
        ax.text(v + 3, i, f'{v:.0f}', va='center', fontsize=9)
    ax.grid(axis='x', alpha=0.3)

    # panel 3: forecaster directional accuracy
    ax = axes[2]
    fnames = sorted(fc_results, key=lambda k: fc_results[k]['DirAcc'])
    da     = [fc_results[n]['DirAcc'] for n in fnames]
    colors = ['#e76f51' if n == 'LSTM' else '#e9c4ba' for n in fnames]
    ax.barh(np.arange(len(fnames)), da, color=colors)
    ax.set_yticks(np.arange(len(fnames)))
    ax.set_yticklabels(fnames)
    ax.axvline(50, color='grey', linestyle='--', linewidth=1)
    ax.text(50.5, -0.45, 'coin flip', fontsize=8, color='grey')
    ax.set_xlabel('Directional accuracy % (higher is better)')
    ax.set_title('Forecaster — direction of price move')
    for i, v in enumerate(da):
        ax.text(v + 0.5, i, f'{v:.1f}%', va='center', fontsize=9)
    ax.grid(axis='x', alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=150, bbox_inches='tight')
    print(f"\nForecaster comparison ({FORECAST_HORIZON_MONTHS}-month ahead, per-crop test windows):")
    for n, r in sorted(fc_results.items(), key=lambda kv: kv[1]['MAE']):
        print(f"  {n:<18} MAE={r['MAE']:>7.2f}  R²={r['R2']:>8.4f}  DirAcc={r['DirAcc']:>5.1f}%")
    print(f"\nChart saved → {OUT_PATH}")


if __name__ == "__main__":
    run()
