import os

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

CLASSIFIER_PATH            = os.path.join(MODELS_DIR, "best_classifier.pkl")
PREPROCESSING_PIPELINE_PATH= os.path.join(MODELS_DIR, "preprocessing_pipeline.pkl")
LABEL_ENCODER_PATH         = os.path.join(MODELS_DIR, "label_encoder.pkl")
FEATURE_COLUMNS_PATH       = os.path.join(MODELS_DIR, "feature_columns.pkl")
LSTM_PATH                  = os.path.join(MODELS_DIR, "lstm_price_forecaster.pt")
LSTM_SCALER_PATH           = os.path.join(MODELS_DIR, "lstm_scaler.pkl")
PRICE_SCALER_PATH          = os.path.join(MODELS_DIR, "price_scaler.pkl")
METADATA_PATH              = os.path.join(MODELS_DIR, "model_metadata.json")

# Training window start — pre-2015 cedi regime differs too much from the
# current one and misleads the scalers
TRAIN_START = '2015-01-01'

# order is significant — must match training exactly
# price and derivatives are log-transformed: log space keeps train/test ranges comparable across the cedi inflation regime shift
LSTM_FEAT_COLS = [
    'price',
    'exchange_rate',
    'month_sin',
    'month_cos',
    'price_lag1',
    'price_lag2',
    'price_lag3',
    'rolling_mean_3',
    'rolling_std_3',
    'crop_Maize',
    'crop_Millet',
    'crop_Sorghum',
    'mkt_Bolga',
    'mkt_Kumasi',
    'mkt_Tamale',
    'mkt_Techiman',
    'mkt_Wa',
]

# 1x24 chosen by experiment — 2x64 overfits ~1,200 sequences (see scripts/lstm_experiment.py)
LSTM_SEQ_LEN  = 6
LSTM_HIDDEN   = 24
LSTM_LAYERS   = 1
LSTM_DROPOUT  = 0.0

CAT_COLS = ['market', 'commodity']

NUM_COLS = [
    'price_lag1', 'price_lag2', 'price_lag3',
    'rolling_mean_3', 'rolling_std_3', 'price_pct_change',
    'exchange_rate',
    'month_sin', 'month_cos',
    'is_harvest_season', 'is_lean_season',
    'price_vs_annual', 'price_yoy',
]

# labels, LSTM target, and storage costs all use this same horizon
FORECAST_HORIZON_MONTHS    = 3

STORAGE_COST_PER_BAG_MONTH = 0.80
STORAGE_MONTHS             = float(FORECAST_HORIZON_MONTHS)

# road freight rate, Northern Ghana; last-mile accounts for village-to-district-centre distance
TRANSPORT_COST_PER_KM  = 0.20
TRANSPORT_LAST_MILE_KM = 10.0

# relative threshold: scale-invariant across price regimes (GHS 200 era vs GHS 1000 era)
STORE_THRESHOLD_PCT = 0.05

VALID_MARKETS     = ['Bolga', 'Kumasi', 'Tamale', 'Techiman', 'Wa']
VALID_COMMODITIES = ['Maize', 'Millet', 'Sorghum']
