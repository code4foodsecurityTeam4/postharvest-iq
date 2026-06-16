# PostHarvest IQ

A USSD-based agricultural decision intelligence service for smallholder cereal farmers in Northern Ghana. Farmers dial `*384#` and answer three questions — crop, district, number of bags — and receive a **STORE** or **SELL NOW** recommendation backed by a machine learning price forecast.

Built for the Blossom Academy Code4FoodSecurity Fellowship 2026.

---

## How it works (end to end)

```
Farmer dials *384#
       ↓
Africa's Talking USSD gateway → POST /ussd
       ↓
ussd_service.py  (manages session, language, bag count)
       ↓
ml_service.py  (orchestrates both models)
    ├── LSTM forecaster   → price in 3 months (GHS)
    └── RF classifier     → STORE or SELL_NOW
       ↓
recommendation_service.py  (net return = forecast gain − storage cost − transport cost)
       ↓
USSD response in English / Dagbani / Hausa
```

---

## Setup

```bash
# Clone
git clone https://github.com/code4foodsecurityTeam4/postharvest-iq.git
cd postharvest-iq

# Environment
conda create -n postharvest python=3.11
conda activate postharvest
pip install -r requirements.txt

# Configure
cp .env.example .env
# Fill in your MySQL credentials in .env

# Database
mysql -u root -p
CREATE DATABASE IF NOT EXISTS postharvest_iq;
EXIT;

# Run migrations to create all tables
alembic upgrade head

# Seed warehouse data (run once after creating the DB)
python scripts/seed_storage_locations.py

# Extend price data to current month
python -m scripts.extend_recent_prices

# Train models
python -m app.ml.train_lstm
python -m app.ml.train_xgboost

# Run API
uvicorn app.main:app --reload --host localhost

# (Optional) Monitoring dashboard
streamlit run dashboard/streamlit_app.py
```

API docs: `http://localhost:8000/docs`

---

## Project structure

```
postharvest-iq/
├── app/                        # Main application (FastAPI)
│   ├── main.py                 # App entry point — wires up all routes
│   ├── config.py               # Reads .env (DB credentials, secrets)
│   ├── core/
│   │   └── database.py         # SQLAlchemy engine, session factory, Base
│   ├── api/routes/
│   │   ├── ussd.py             # POST /ussd — Africa's Talking webhook
│   │   ├── forecasts.py        # GET /forecasts/{district}/{crop}
│   │   ├── recommendations.py  # GET /recommendations history
│   │   ├── storage.py          # GET /storage — nearby facility lookup
│   │   └── dashboard.py        # GET /dashboard — summary stats for Streamlit
│   ├── ml/
│   │   ├── config.py           # All ML hyperparameters and file paths
│   │   ├── train_lstm.py       # Trains the LSTM price forecaster
│   │   ├── train_xgboost.py    # Trains the STORE/SELL classifier (5-algorithm tournament)
│   │   ├── predict.py          # Loads saved models and runs inference
│   │   └── models/             # Saved model artifacts (see below)
│   ├── models/                 # SQLAlchemy ORM table definitions
│   │   ├── wfp_price.py        # wfp_prices table
│   │   ├── wfp_market.py       # wfp_markets table (with GPS)
│   │   ├── storage.py          # storage_locations table
│   │   ├── recommendation.py   # recommendations table (logged per USSD session)
│   │   ├── exchange_rate.py    # ghana_exchange_rates table
│   │   ├── forecast.py         # price_forecasts table
│   │   └── producer_price.py   # fao_producer_prices table
│   └── services/
│       ├── ml_service.py       # Orchestrates LSTM + classifier + economic calc
│       ├── recommendation_service.py  # Net return formula, STORE/SELL_NOW threshold
│       ├── storage_service.py  # Haversine distance → nearest GCX warehouse
│       ├── strings.py          # All user-facing text in English, Dagbani, Hausa
│       └── ussd_service.py     # USSD session state machine (levels 0–5)
│
├── scripts/
│   ├── extend_recent_prices.py          # Extends price data to current month
│   ├── auto_retrain.py                  # Retrains models when new WFP data arrives
│   ├── evaluate_past_recommendations.py # Scores past STORE/SELL calls against actuals
│   ├── lstm_experiment.py               # Architecture search that selected 1×24 LSTM
│   ├── plot_model_competition.py        # Generates the 3-panel benchmark chart
│   └── seed_storage_locations.py        # Seeds GCX warehouse rows into the DB
│
├── data/
│   ├── raw/                    # Original CSV files from WFP, FAO, ClearGlobal
│   └── processed/
│       └── cereals_merged_clean.csv     # Cleaned merged dataset used in notebooks
│
├── dashboard/
│   └── streamlit_app.py        # Streamlit monitoring dashboard (price trends, activity)
│
├── migrations/
│   └── versions/
│       └── 1c7341e28d12_initial_schema.py   # Alembic migration — creates all tables
│
├── notebooks/
│   ├── 02_data_cleaning.ipynb  # Data cleaning and merging pipeline
│   ├── 03_eda.ipynb            # Exploratory data analysis (price trends, seasonality)
│   └── figures/                # EDA charts exported as PNG
│
├── Procfile                    # Heroku/Railway process definition (uvicorn)
├── requirements.txt            # Python dependencies
├── alembic.ini                 # Alembic database migration config
└── .gitignore
```

---

## app/main.py

Entry point. Starts FastAPI, runs Alembic migrations on boot, and registers all route prefixes. If the database has tables but no migration history, it refuses to start to prevent schema corruption.

---

## app/config.py

Reads environment variables from `.env` — database host, user, password, port, and database name. Used by `database.py` to build the connection string.

---

## app/core/database.py

Creates the SQLAlchemy engine and session factory. `get_db()` is a FastAPI dependency that opens a session per request and closes it after.

---

## app/api/routes/

| File | Endpoint | What it does |
|---|---|---|
| `ussd.py` | `POST /ussd` | Receives Africa's Talking USSD webhook, delegates to `ussd_service`, returns plain-text USSD response |
| `forecasts.py` | `GET /forecasts/{district}/{crop}` | Returns LSTM price forecast + interval for a given district and crop |
| `recommendations.py` | `GET /recommendations` | Returns logged recommendation history from the database |
| `storage.py` | `GET /storage` | Returns nearest verified storage facilities for a crop and district |
| `dashboard.py` | `GET /dashboard` | Returns summary data (recent prices, recommendation counts) for the Streamlit dashboard |

---

## app/ml/config.py

Single source of truth for all ML constants. Changing a value here affects both training and serving automatically.

| Constant | Value | Meaning |
|---|---|---|
| `TRAIN_START` | 2015-01-01 | Training data start — pre-2015 cedi regime distorts scalers |
| `LSTM_FEAT_COLS` | 17 columns | Exact feature order the LSTM expects (order matters) |
| `LSTM_SEQ_LEN` | 6 | Months of history fed into the LSTM per prediction |
| `LSTM_HIDDEN` | 24 | Hidden units — chosen by experiment to avoid overfitting ~1,200 sequences |
| `FORECAST_HORIZON_MONTHS` | 3 | How many months ahead to forecast and label |
| `STORAGE_COST_PER_BAG_MONTH` | 0.80 GHS | GCX confirmed warehouse rate |
| `TRANSPORT_COST_PER_KM` | 0.20 GHS | Road freight rate, Northern Ghana |
| `TRANSPORT_LAST_MILE_KM` | 10.0 km | Average village-to-district-centre distance added to GPS distance |
| `STORE_THRESHOLD_PCT` | 0.05 | Net gain must exceed 5% of current price to label STORE — scale-invariant across price regimes |

---

## app/ml/train_lstm.py

Trains a single global LSTM across all 15 market-crop series (5 markets × 3 crops).

**Step by step:**

1. Queries `wfp_prices` joined with `ghana_exchange_rates` for all 15 series from 2015
2. Applies log transform to prices — makes the inflationary price climb linear so train and test distributions stay comparable
3. Computes lag features (lag1, lag2, lag3), rolling mean/std, and adds crop and market one-hot columns
4. Sets `target` = log price 3 months ahead (direct multi-step, not recursive)
5. Splits each series chronologically 70/15/15, then stacks all 15 series together
6. Fits a `MinMaxScaler` on features and a separate one on the target (both fit on training data only)
7. Trains a 1-layer LSTM (hidden=24) with Adam optimiser, early stopping (patience=15), and gradient clipping
8. Evaluates on the test split, transforms predictions back to GHS via `exp(inverse_transform(...))`
9. Saves model weights, both scalers, and per-crop metrics to `app/ml/models/`

```bash
python -m app.ml.train_lstm
```

---

## app/ml/train_xgboost.py

Runs a 5-algorithm tournament to find the best STORE/SELL_NOW classifier.

**Step by step:**

1. Queries the same price data and engineers 13 numeric features (price lags, rolling stats, seasonality flags, year-on-year change, exchange rate)
2. Creates binary labels: `STORE` if `(forecast_price − current_price − storage_cost − transport_cost) > 5% of current_price`, else `SELL_NOW`
3. Compares SMOTE oversampling vs class-weight balancing — picks whichever gives higher validation F1
4. Runs `RandomizedSearchCV` with `TimeSeriesSplit(n_splits=5)` for Random Forest, Gradient Boosting, Decision Tree, and Logistic Regression; runs a manual grid search for XGBoost
5. Selects the algorithm with the highest **validation** F1 (not test, to avoid leakage)
6. Saves the winning model, preprocessing pipeline, and label encoder
7. Persists all tournament results into `model_metadata.json`

```bash
python -m app.ml.train_xgboost
```

---

## app/ml/predict.py

Loads all saved model artifacts at import time (once, in memory for every request).

| Function | What it does |
|---|---|
| `forecast_price(seq_df)` | Takes a DataFrame of recent monthly rows, scales them, runs the LSTM, inverts the log transform, returns GHS price |
| `predict_decision(input_df)` | Takes a single feature row, runs it through the preprocessing pipeline and classifier, returns `STORE`/`SELL_NOW` with confidence |
| `get_model_info()` | Returns the full metadata dict (metrics, per-crop MAE, classifier name) |

---

## app/services/ml_service.py

Orchestrates everything for a single farmer request.

**`get_forecast(crop, district, db)`**
- Fetches the last 12 months of prices from the DB
- Builds the 17-feature sequence the LSTM expects (log prices, lags, one-hots)
- Calls `forecast_price()` and wraps the result with a `±MAE` uncertainty interval pulled from metadata

**`get_recommendation(crop, district, quantity_bags, ...)`**
- Calls `get_forecast` for the LSTM price
- Looks up the nearest storage facility → computes actual transport cost from GPS distance (`(distance_km + 10 km last-mile) × 0.20 GHS/km`)
- Calls `calculate_net_return` with the real transport cost
- Calls `predict_decision` for the RF classifier decision
- Classifier result takes priority; economic calculation is the fallback
- Logs the recommendation to the `recommendations` table
- Returns `forecast_low`, `forecast_high`, `net_per_bag`, `net_total`, `current_price`, `transport_cost`

---

## app/services/recommendation_service.py

Pure economics — no ML.

```
net_per_bag = (forecast_price − current_price) − (0.80 × 3 months) − transport_cost
decision    = STORE if net_per_bag > 5% of current_price else SELL_NOW
net_total   = net_per_bag × number_of_bags
```

The 5% threshold makes the decision scale-invariant — it means the same economic signal whether the price is GHS 200 or GHS 1,000.

---

## app/services/storage_service.py

**`get_nearest_storage(district, crop, db)`**
- Queries `storage_locations` filtered by crop type and active/verified status
- Computes Haversine distance from the farmer's district centre to each facility
- Returns the 3 closest, sorted by distance

**`get_nearest_market(district, db)`**
- Looks up the WFP market GPS from `wfp_markets`
- Returns market name and distance from the district centre

---

## app/services/strings.py

All user-facing text in three languages. The `t(lang, key)` function looks up a key for the given language and falls back to English for any missing entry.

| Language | Code |
|---|---|
| English | `en` |
| Dagbani | `dag` |
| Hausa | `hau` |

Key strings shown on the USSD recommendation screen:

| Key | English | Dagbani | Hausa |
|---|---|---|---|
| `store` | STORE your crop | KPAGI ni masara | ADANA masararka |
| `price_today` | Price today: GHS {price} per bag | Nyɛɛri daa: GHS {price} baŋ | Farashi yau: GHS {price} a buhu |
| `forecast_range` | In 3 months: GHS {low}-{high} | Kodili 3 dali: GHS {low}-{high} | Wata 3 masu zuwa: GHS {low}-{high} |
| `earn_per_bag` | Net gain: GHS {gain}/bag | Paɣa kpeŋ: GHS {gain}/baŋ | Riba bayan kuɗi: GHS {gain}/buhu |
| `total_for_bags` | {bags} bags = GHS {net} total | Bagi {bags} = GHS {net} kpeŋ | Buhu {bags} = GHS {net} jimla |

---

## app/services/ussd_service.py

A state machine driven by the USSD text string. Africa's Talking concatenates each farmer input with `*`, so `"1*2*1*30"` means: English → Maize → Tamale → 30 bags.

| Level | Input | Response |
|---|---|---|
| 0 | (first dial) | Language selection |
| 1 | Language chosen | Crop selection (Maize / Millet / Sorghum) |
| 2 | Crop chosen | District selection (Tamale / Bolgatanga / Wa) |
| 3 | District chosen | Ask for number of bags |
| 4 | Bags entered | Full recommendation: decision + price today + 3-month forecast range + net gain per bag + total |
| 5 | Action chosen | Find storage / Sell all now / Sell half store half / Exit |

**STORE screen (level 4) shows:**
```
STORE your crop
Price today: GHS 538 per bag
In 3 months: GHS 600-788
Net gain: GHS 87/bag
30 bags = GHS 2,610 total
```

**SELL NOW screen (level 4) shows:**
```
SELL NOW
GHS 538 per bag
30 bags = GHS 16,140 today
```

Prefixing the session with `9*{month}*` activates demo mode, overriding the current month — used for testing seasonal behaviour without waiting for the right time of year.

---

## app/models/

SQLAlchemy ORM classes that map to MySQL tables. Used by routes and services to query the database with Python objects instead of raw SQL.

| File | Table | Contains |
|---|---|---|
| `wfp_price.py` | `wfp_prices` | Monthly wholesale grain prices per market. `priceflag='synthetic'` marks rows generated by `extend_recent_prices.py` |
| `wfp_market.py` | `wfp_markets` | Market names with GPS coordinates used for Haversine distance |
| `storage.py` | `storage_locations` | GCX warehouses with GPS, capacity, cost per bag, contact number |
| `recommendation.py` | `recommendations` | Every USSD recommendation logged with price, decision, bags, phone number, session |
| `exchange_rate.py` | `ghana_exchange_rates` | Monthly GHS/USD exchange rates. `flag='synth'` marks extended rows |
| `forecast.py` | `price_forecasts` | Cached LSTM forecasts |
| `producer_price.py` | `fao_producer_prices` | FAO producer price index (loaded but not used in the current model) |

---

## scripts/extend_recent_prices.py

WFP data ends in mid-2023. This script extends every market-crop series to the current month with synthetic prices so the models train on current price ranges.

**How synthetic prices are generated:**
- Anchors to the last real price for each series
- Removes the seasonal factor to get the underlying monthly base level
- Applies a monthly drift: `+2.2%/month` for 2024 (cedi depreciation era), `−0.3%/month` for 2025 (cedi recovery), `+0.2%/month` for 2026 (stable cedi, background inflation only)
- Multiplies back by a seasonal factor (prices dip Oct–Dec at harvest, peak Jun–Aug lean season)
- Adds AR(1) noise (autocorrelated, like real price series)
- Tags all rows with `priceflag='synthetic'` so they can be deleted and regenerated safely

```bash
python -m scripts.extend_recent_prices
# To undo: DELETE FROM wfp_prices WHERE priceflag='synthetic';
```

---

## scripts/auto_retrain.py

Checks whether new WFP price data has arrived since the last training run. If so, retrains both the LSTM and the classifier. Run this monthly after ingesting new WFP data.

**Logic:**
1. `latest_real_data_date()` — queries `MAX(date)` from `wfp_prices` where `priceflag != 'synthetic'`
2. `last_retrain_date()` — reads `last_retrain_date` from `model_metadata.json`
3. If latest > trained (or `--force` flag): retrains LSTM → retrains classifier → stamps new retrain date

```bash
python -m scripts.auto_retrain           # only retrains if new data exists
python -m scripts.auto_retrain --force   # retrains regardless
```

---

## scripts/evaluate_past_recommendations.py

Feedback loop. For every recommendation logged approximately 3 months ago, looks up what the actual price turned out to be in `wfp_prices` and scores whether the STORE/SELL_NOW decision was correct.

**Logic:**
1. Fetches recommendations from `~3 months ago ± 2 weeks` from the `recommendations` table
2. For each, looks up the actual price at recommendation date + 3 months in `wfp_prices` (±15 day window)
3. Recomputes whether STORE was economically justified given that actual price
4. Prints accuracy report with per-recommendation breakdown

```bash
python -m scripts.evaluate_past_recommendations
```

Sample output:
```
  ID  Date        Crop     District     Decision  Current  Forecast   Actual      Net  OK
  --  ----------  -------  -----------  --------  -------  --------  -------  -------  --
   1  2026-03-10  Maize    Tamale       STORE       538       714      756       165.6  ✓
   2  2026-03-12  Millet   Bolgatanga   SELL_NOW    612       598      590       -54.4  ✓

Accuracy: 2/2 = 100.0%
```

---

## scripts/lstm_experiment.py

The architecture search that decided the production LSTM. Trains three LSTM variants (2×64, 1×24, 1×16) alongside XGBoost regressor, Random Forest regressor, Naive baseline, and SARIMA on identical data and identical splits.

Results that drove the final choice:
```
XGB Regressor      MAE= 66   R²=0.85   DirAcc=69%
RF Regressor       MAE= 82   R²=0.80   DirAcc=57%
LSTM 1×24          MAE= 92   R²=0.71   DirAcc=61%  ← deployed
LSTM 1×16          MAE= 97   R²=0.67   DirAcc=51%
LSTM 2×64          MAE= 98   R²=0.71   DirAcc=41%  ← overfits
Naive              MAE=113   R²=0.67   DirAcc=40%
SARIMA             MAE=297   R²=-1.67  DirAcc=60%
```

LSTM was chosen over XGB/RF because it produces market-specific sequential forecasts, not a flat scalar from a single feature snapshot.

```bash
python -m scripts.lstm_experiment
```

---

## scripts/plot_model_competition.py

Generates the 3-panel benchmark chart saved to `app/ml/models/model_competition.png`:
- Panel 1: Classifier tournament (val and test F1 for all 5 algorithms)
- Panel 2: Forecaster MAE comparison (lower is better)
- Panel 3: Forecaster directional accuracy (higher is better)

```bash
python -m scripts.plot_model_competition
```

---

## app/ml/models/ (saved artifacts)

| File | What it is |
|---|---|
| `lstm_price_forecaster.pt` | Trained LSTM weights (PyTorch) |
| `lstm_scaler.pkl` | MinMaxScaler fitted on the 17 LSTM input features (fit on training data only) |
| `price_scaler.pkl` | MinMaxScaler fitted on the log-price target (fit on training data only) |
| `best_classifier.pkl` | Winning classifier from the tournament (Random Forest, Val F1=0.82, Test F1=0.95) |
| `preprocessing_pipeline.pkl` | ColumnTransformer: OneHotEncoder for market/crop + passthrough for numerics |
| `label_encoder.pkl` | Maps SELL_NOW/STORE ↔ integer |
| `feature_columns.pkl` | Ordered list of classifier feature names |
| `model_metadata.json` | All training metrics, per-crop MAE, classifier tournament results, last retrain date |
| `model_competition.png` | 3-panel benchmark chart |

---

## data/

| Path | Contents |
|---|---|
| `data/raw/wfp_food_prices_gha.csv` | WFP monthly wholesale grain prices, Ghana |
| `data/raw/ghana_exchange_rates.csv` | FAO GHS/USD monthly exchange rates |
| `data/raw/wfp_markets_gha.csv` | GPS coordinates for all WFP-monitored markets |
| `data/raw/ghana_producer_prices.csv` | FAO producer price index |
| `data/raw/clearglobal_language_*.csv` | Language distribution by district (used to set USSD default language) |
| `data/processed/cereals_merged_clean.csv` | Cleaned and merged dataset used in EDA notebooks |
| `data/load_data.py` | Reads the CSVs and loads them into MySQL |

---

## dashboard/streamlit_app.py

A Streamlit monitoring dashboard for administrators. Shows recent price trends, recommendation activity, and model metadata. Calls the `/dashboard` API endpoint for data.

```bash
streamlit run dashboard/streamlit_app.py
```

---

## migrations/

Alembic database migration files. The single migration `1c7341e28d12_initial_schema.py` creates all tables. Run on every fresh database:

```bash
alembic upgrade head
```

---

## notebooks/

| File | What it contains |
|---|---|
| `02_data_cleaning.ipynb` | Merges WFP prices, exchange rates, and producer prices; removes duplicates; handles missing values |
| `03_eda.ipynb` | Exploratory analysis: seasonal price cycles, market comparisons, FX correlation, class distribution for STORE/SELL labels |
| `postharvest_iq_model.ipynb` | Early model prototyping notebook (superseded by the training scripts) |

---

## Config files

| File | Purpose |
|---|---|
| `Procfile` | `web: uvicorn app.main:app` — tells Heroku/Railway how to start the server |
| `requirements.txt` | Python dependencies for the full stack |
| `requirements-backend.txt` | Dependencies for the API only (lighter, for deployment) |
| `runtime.txt` | Python version pin for deployment |
| `alembic.ini` | Points Alembic at the database URL and migration folder |
| `.gitignore` | Excludes `.env`, raw data, `__pycache__`, training checkpoint files |

---

## Key design decisions

**Why log-price transform?**
Ghana's cedi depreciated sharply between 2021–2024, pushing food prices from ~GHS 200 to ~GHS 1,000. A model trained in raw GHS space would see the test period as completely out of distribution. Log transform makes the inflationary trend linear so the LSTM sees a stable range across the full training window.

**Why a relative 5% threshold for STORE labels?**
A fixed nominal threshold (e.g. "profit > GHS 20") means different things in different years. 5% of the current price means the same economic signal whether the price is GHS 200 or GHS 1,000.

**Why LSTM over XGBoost for forecasting?**
XGBoost produces a lower MAE (66 vs 92 GHS) on the test set, but it predicts from a single feature snapshot and cannot naturally generate a price trajectory for a specific market 3 months ahead. The LSTM takes a 6-month sequence including market identity, making its output directly usable in the per-market economic calculation.

**Why one global LSTM across all 15 series?**
Training one model per crop gives ~240 sequences each — too few for a network with tens of thousands of parameters. Pooling all 15 market-crop series gives ~1,200 sequences and makes the model aware of cross-market patterns.

**Why dynamic transport cost from GPS?**
A fixed GHS 2.00 transport cost is the same for a farmer 5 km from a storage facility and one 80 km away — which produces different true economics. Using Haversine distance from the WFP market GPS plus a 10 km last-mile offset gives realistic per-district variation (Tamale ~GHS 2.09, Bolgatanga ~GHS 2.15, Wa ~GHS 2.00).

---

## Rules

- Never push directly to `main`
- Always create a branch: `git checkout -b feature/your-task`
- Open a pull request and get one approval before merging
