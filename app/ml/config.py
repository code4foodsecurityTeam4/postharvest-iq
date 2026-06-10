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

# must match training notebook exactly — order is significant
LSTM_FEAT_COLS = [
    'price',
    'exchange_rate',
    'producer_price_index',
    'month_sin',
    'month_cos',
    'price_lag1',
    'price_lag2',
    'price_lag3',
    'rolling_mean_3',
    'rolling_std_3',
]

# must match training notebook exactly — order is significant
LSTM_SEQ_LEN  = 12
LSTM_HIDDEN   = 64
LSTM_LAYERS   = 2
LSTM_DROPOUT  = 0.2

CAT_COLS = ['market', 'commodity']

NUM_COLS = [
    'price_lag1', 'price_lag2', 'price_lag3',
    'rolling_mean_3', 'rolling_std_3', 'price_pct_change',
    'exchange_rate', 'producer_price_index',
    'month_sin', 'month_cos',
    'is_harvest_season', 'is_lean_season',
    'price_vs_annual', 'price_yoy',
]

STORAGE_COST_PER_BAG_MONTH = 0.80
STORAGE_MONTHS             = 1.5
TRANSPORT_COST             = 2.0
STORE_THRESHOLD            = 20.0
PARTIAL_THRESHOLD          = 5.0

VALID_MARKETS     = ['Bolga', 'Kumasi', 'Tamale', 'Techiman', 'Wa']
VALID_COMMODITIES = ['Maize', 'Millet', 'Sorghum']
