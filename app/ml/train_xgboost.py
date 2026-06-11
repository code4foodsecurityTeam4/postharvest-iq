# Run: python -m app.ml.train_xgboost

import json
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.metrics import f1_score, classification_report
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from imblearn.over_sampling import SMOTE
from scipy.stats import randint, uniform
import xgboost as xgb

from app.core.database import engine
from app.ml.config import (
    CLASSIFIER_PATH, PREPROCESSING_PIPELINE_PATH, LABEL_ENCODER_PATH,
    FEATURE_COLUMNS_PATH, METADATA_PATH,
    CAT_COLS, NUM_COLS,
    STORAGE_COST_PER_BAG_MONTH, STORAGE_MONTHS, TRANSPORT_COST,
    STORE_THRESHOLD, PARTIAL_THRESHOLD,
)

SEED = 42
TRAIN_RATIO, VAL_RATIO = 0.70, 0.15


def load_and_engineer(engine) -> pd.DataFrame:
    """Load data from MySQL and apply the same feature engineering as the notebook."""
    query = """
        SELECT
            p.date, p.market, p.commodity, p.price,
            SIN(2 * PI() * MONTH(p.date) / 12) AS month_sin,
            COS(2 * PI() * MONTH(p.date) / 12) AS month_cos,
            fx.value   AS exchange_rate,
            pp.value   AS producer_price_index
        FROM wfp_prices p
        LEFT JOIN ghana_exchange_rates fx
            ON fx.year   = YEAR(p.date)
            AND fx.months = DATE_FORMAT(p.date, '%M')
            AND fx.element = 'Local currency units per USD'
        LEFT JOIN fao_producer_prices pp
            ON pp.year   = YEAR(p.date)
            AND pp.item  = p.commodity
            AND pp.months = 'Annual value'
            AND pp.element = 'Producer Price Index (2014-2016 = 100)'
        WHERE p.commodity IN ('Maize', 'Millet', 'Sorghum')
          AND p.pricetype = 'Wholesale'
          AND p.market IN ('Tamale', 'Bolga', 'Wa', 'Kumasi', 'Techiman')
        ORDER BY p.market, p.commodity, p.date
    """
    df = pd.read_sql(query, engine)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['market','commodity','date']).reset_index(drop=True)

    grp = df.groupby(['market','commodity'])['price']
    df['price_lag1']       = grp.shift(1)
    df['price_lag2']       = grp.shift(2)
    df['price_lag3']       = grp.shift(3)
    df['rolling_mean_3']   = grp.transform(lambda x: x.rolling(3, min_periods=1).mean())
    df['rolling_std_3']    = grp.transform(lambda x: x.rolling(3, min_periods=2).std())
    df['price_pct_change'] = grp.pct_change()
    df['price_next']       = grp.shift(-1)
    df['month']            = df['date'].dt.month
    df['is_harvest_season']= df['month'].isin([10,11,12]).astype(int)
    df['is_lean_season']   = df['month'].isin([6,7,8]).astype(int)
    df['price_vs_annual']  = df['price'] / grp.transform(
        lambda x: x.rolling(12, min_periods=6).mean())
    df['price_yoy']        = grp.pct_change(12)

    df = df.dropna(subset=['price_lag1','price_lag2','price_lag3','rolling_std_3',
                            'price_pct_change','price_next','price_vs_annual','price_yoy'])
    df = df.sort_values('date').reset_index(drop=True)

    def make_label(row):
        net = ((row['price_next'] - row['price'])
               - (STORAGE_COST_PER_BAG_MONTH * STORAGE_MONTHS) - TRANSPORT_COST)
        if net > STORE_THRESHOLD:    return 'STORE'
        elif net > PARTIAL_THRESHOLD: return 'SELL_PARTIAL'
        else:                         return 'SELL_NOW'

    df['decision'] = df.apply(make_label, axis=1)
    return df


def retrain():
    print("Loading and engineering features from MySQL...")
    df = load_and_engineer(engine)
    print(f"Total rows: {len(df)}")

    # Chronological split
    n = len(df); n_tr = int(n*TRAIN_RATIO); n_va = int(n*VAL_RATIO)
    df_tr = df.iloc[:n_tr].copy()
    df_va = df.iloc[n_tr:n_tr+n_va].copy()
    df_te = df.iloc[n_tr+n_va:].copy()

    print(f"Train:{len(df_tr)}  Val:{len(df_va)}  Test:{len(df_te)}")

    # Fit ColumnTransformer on train only
    preprocessor = ColumnTransformer(transformers=[
        ('ohe', OneHotEncoder(handle_unknown='ignore', sparse_output=False), CAT_COLS),
        ('num', 'passthrough', NUM_COLS),
    ])
    preprocessor.fit(df_tr[CAT_COLS + NUM_COLS])

    ohe_cols = preprocessor.named_transformers_['ohe'].get_feature_names_out(CAT_COLS).tolist()
    FEATURES  = ohe_cols + NUM_COLS

    X_tr = preprocessor.transform(df_tr[CAT_COLS + NUM_COLS])
    X_va = preprocessor.transform(df_va[CAT_COLS + NUM_COLS])
    X_te = preprocessor.transform(df_te[CAT_COLS + NUM_COLS])

    label_encoder = LabelEncoder()
    y_tr = label_encoder.fit_transform(df_tr['decision'].values)
    y_va = label_encoder.transform(df_va['decision'].values)
    y_te = label_encoder.transform(df_te['decision'].values)
    class_names = label_encoder.classes_.tolist()
    print(f"Classes: {class_names}")

    # Compare class weights vs SMOTE
    rf_cw = RandomForestClassifier(n_estimators=100, class_weight='balanced',
                                    max_depth=5, random_state=SEED, n_jobs=-1)
    rf_cw.fit(X_tr, y_tr)
    f1_cw = f1_score(y_va, rf_cw.predict(X_va), average='macro')

    min_cc = min(np.unique(y_tr, return_counts=True)[1])
    smote  = SMOTE(random_state=SEED, k_neighbors=min(5, min_cc-1))
    X_sm, y_sm = smote.fit_resample(X_tr, y_tr)
    rf_sm = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=SEED, n_jobs=-1)
    rf_sm.fit(X_sm, y_sm)
    f1_sm = f1_score(y_va, rf_sm.predict(X_va), average='macro')

    USE_SMOTE     = f1_sm > f1_cw
    X_TRAIN_FINAL = X_sm if USE_SMOTE else X_tr
    Y_TRAIN_FINAL = y_sm if USE_SMOTE else y_tr
    print(f"Balance method: {'SMOTE' if USE_SMOTE else 'class_weight=balanced'}")

    CW = 'balanced' if not USE_SMOTE else None
    param_grids = {
        'Random Forest': {
            'n_estimators':      randint(50,150), 'max_depth':         randint(3,6),
            'min_samples_split': randint(10,30),  'min_samples_leaf':  randint(5,15),
            'max_features':      ['sqrt'],
        },
        'Gradient Boosting': {
            'n_estimators': randint(50,150), 'max_depth':     randint(2,3),
            'learning_rate':uniform(0.01,0.1),'subsample':    uniform(0.5,0.4),
        },
        'Decision Tree': {
            'max_depth':randint(2,5),'min_samples_split':randint(15,40),
            'min_samples_leaf':randint(8,20),'criterion':['gini','entropy'],
        },
        'Logistic Regression': {
            'C':uniform(0.001,1.0),'solver':['lbfgs','saga'],'max_iter':randint(500,2000),
        },
    }
    base_models = {
        'Random Forest':       RandomForestClassifier(class_weight=CW,
                                   random_state=SEED, n_jobs=-1),
        'Gradient Boosting':   GradientBoostingClassifier(random_state=SEED),
        'Decision Tree':       DecisionTreeClassifier(class_weight=CW, random_state=SEED),
        'Logistic Regression': LogisticRegression(class_weight=CW,
                                   random_state=SEED, max_iter=1000),
    }

    tscv = TimeSeriesSplit(n_splits=5)
    results = {}
    print("\nTraining all algorithms...")

    # XGBoost: manual search to avoid sklearn __sklearn_tags__ incompatibility
    _rng = np.random.default_rng(SEED)
    _xgb_candidates = [
        {
            'n_estimators':     int(_rng.integers(50, 150)),
            'max_depth':        int(_rng.integers(2, 4)),
            'learning_rate':    float(_rng.uniform(0.05, 0.20)),
            'subsample':        float(_rng.uniform(0.5, 1.0)),
            'colsample_bytree': float(_rng.uniform(0.5, 1.0)),
            'min_child_weight': int(_rng.integers(5, 20)),
        }
        for _ in range(30)
    ]
    _best_cv, _best_xgb_params = -1.0, _xgb_candidates[0]
    for _params in _xgb_candidates:
        _fold_scores = []
        for _tr_idx, _va_idx in tscv.split(X_TRAIN_FINAL):
            _m = xgb.XGBClassifier(eval_metric='mlogloss', random_state=SEED, **_params)
            _m.fit(X_TRAIN_FINAL[_tr_idx], Y_TRAIN_FINAL[_tr_idx])
            _fold_scores.append(f1_score(Y_TRAIN_FINAL[_va_idx], _m.predict(X_TRAIN_FINAL[_va_idx]), average='macro'))
        _score = float(np.mean(_fold_scores))
        if _score > _best_cv:
            _best_cv, _best_xgb_params = _score, _params
    _xgb_best = xgb.XGBClassifier(eval_metric='mlogloss', random_state=SEED, **_best_xgb_params)
    _xgb_best.fit(X_TRAIN_FINAL, Y_TRAIN_FINAL)
    _f1_va = f1_score(y_va, _xgb_best.predict(X_va), average='macro')
    _f1_te = f1_score(y_te, _xgb_best.predict(X_te), average='macro')
    results['XGBoost'] = {
        'model': _xgb_best, 'f1_cv': _best_cv,
        'f1_val': _f1_va, 'f1_test': _f1_te,
        'gap': f1_score(Y_TRAIN_FINAL, _xgb_best.predict(X_TRAIN_FINAL), average='macro') - _f1_te,
        'params': _best_xgb_params, 'preds': _xgb_best.predict(X_te),
    }
    print(f"  {'XGBoost':<25} Val F1={_f1_va:.4f}  Test F1={_f1_te:.4f}")

    for name, base in base_models.items():
        search = RandomizedSearchCV(base, param_grids[name], n_iter=30, cv=tscv,
                                     scoring='f1_macro', n_jobs=-1,
                                     random_state=SEED, refit=True)
        search.fit(X_TRAIN_FINAL, Y_TRAIN_FINAL)
        best  = search.best_estimator_
        f1_va = f1_score(y_va, best.predict(X_va), average='macro')
        f1_te = f1_score(y_te, best.predict(X_te), average='macro')
        results[name] = {'model':best,'f1_cv':search.best_score_,
                          'f1_val':f1_va,'f1_test':f1_te,
                          'gap':f1_score(Y_TRAIN_FINAL,best.predict(X_TRAIN_FINAL),
                                         average='macro') - f1_te,
                          'params':search.best_params_,'preds':best.predict(X_te)}
        print(f"  {name:<25} Val F1={f1_va:.4f}  Test F1={f1_te:.4f}")

    best_name = max(results, key=lambda k: results[k]['f1_val'])
    best_res  = results[best_name]
    print(f"\n Best: {best_name}  (Val F1={best_res['f1_val']:.4f})")
    print(classification_report(
        label_encoder.inverse_transform(y_te),
        label_encoder.inverse_transform(best_res['preds']),
        target_names=class_names
    ))

    joblib.dump(best_res['model'], CLASSIFIER_PATH)
    joblib.dump(preprocessor,      PREPROCESSING_PIPELINE_PATH)
    joblib.dump(label_encoder,     LABEL_ENCODER_PATH)
    joblib.dump(FEATURES,          FEATURE_COLUMNS_PATH)

    # Update metadata preserving LSTM fields
    try:
        with open(METADATA_PATH) as f:
            metadata = json.load(f)
    except FileNotFoundError:
        metadata = {}

    metadata.update({
        'best_classifier':  best_name,
        'best_params':      {k:str(v) for k,v in best_res['params'].items()},
        'val_macro_f1':     round(best_res['f1_val'],4),
        'test_macro_f1':    round(best_res['f1_test'],4),
        'overfit_gap':      round(best_res['gap'],4),
        'balance_method':   'SMOTE' if USE_SMOTE else 'class_weight=balanced',
        'features':         FEATURES,
        'decision_classes': class_names,
    })
    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\nAll classifier artifacts saved ")


if __name__ == "__main__":
    retrain()