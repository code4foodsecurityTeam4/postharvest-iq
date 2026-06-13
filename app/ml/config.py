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

# must match training notebook exactly — order is significant
# NOTE: 'price' and its lag/rolling derivatives are log-transformed; the
# inflationary climb is multiplicative, so log space keeps train and test
# ranges comparable
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

# must match training notebook exactly — order is significant
# network sized to data volume (~1,200 training sequences across 15 series);
# the 2x64 variant overfits — see scripts/lstm_experiment.py
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

# Decision horizon: store through the post-harvest trough (~Oct -> Jan).
# Labels, the LSTM target, and storage costs all use this same horizon.
FORECAST_HORIZON_MONTHS    = 3

STORAGE_COST_PER_BAG_MONTH = 0.80
STORAGE_MONTHS             = float(FORECAST_HORIZON_MONTHS)

# Transport: GHS per km per bag (road freight rate, Northern Ghana)
# plus a last-mile offset for the average village-to-district-centre distance
TRANSPORT_COST_PER_KM  = 0.20
TRANSPORT_LAST_MILE_KM = 10.0   # km added on top of GPS distance to storage

# STORE if net gain exceeds this fraction of the current price —
# relative so the label means the same thing across price regimes
STORE_THRESHOLD_PCT = 0.05

VALID_MARKETS     = ['Bolga', 'Kumasi', 'Tamale', 'Techiman', 'Wa']
VALID_COMMODITIES = ['Maize', 'Millet', 'Sorghum']
