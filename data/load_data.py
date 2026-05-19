import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME = (
    os.environ[k] for k in [
        'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'DB_NAME'
    ]
)

engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# load markets
markets = pd.read_csv("data/raw/wfp_markets_gha.csv")
markets.columns = markets.columns.str.lower()
markets.to_sql("wfp_markets", engine, if_exists="replace", index=False)
print(f"Markets loaded: {len(markets)}")

# load prices
prices = pd.read_csv("data/raw/wfp_food_prices_gha.csv")
prices.columns = prices.columns.str.lower()
prices.to_sql("wfp_prices", engine, if_exists="replace", index=False)
print(f"Prices loaded: {len(prices)}")

missing = []

# load exchange rates
try:
    fx = pd.read_csv("data/raw/ghana_exchange_rates.csv")
    fx.columns = fx.columns.str.lower()
    fx.to_sql(
        "ghana_exchange_rates", engine,
        if_exists="replace", index=False
    )
    print(f"Exchange rates loaded: {len(fx)}")
except FileNotFoundError:
    print("WARNING: ghana_exchange_rates.csv not found")
    missing.append("ghana_exchange_rates")

# load producer prices
try:
    producer = pd.read_csv("data/raw/ghana_producer_prices.csv")
    producer.columns = producer.columns.str.lower()
    producer.to_sql(
        "fao_producer_prices", engine,
        if_exists="replace", index=False
    )
    print(f"Producer prices loaded: {len(producer)}")
except FileNotFoundError:
    print("WARNING: ghana_producer_prices.csv not found")
    missing.append("fao_producer_prices")

# load language data — region level (admin1)
# shows which languages are spoken per region
# used to set language defaults in ussd flow per district
try:
    lang1 = pd.read_csv(
        "data/raw/clearglobal_language_use_gha_admin1.csv"
    )
    lang1.columns = lang1.columns.str.lower()
    lang1.to_sql(
        "language_admin1", engine,
        if_exists="replace", index=False
    )
    print(f"Language admin1 loaded: {len(lang1)}")
except FileNotFoundError:
    print("WARNING: language admin1 file not found")

# load language data — district level (admin2)
# more detailed than admin1
# confirms dagbani and hausa dominance in our target districts
try:
    lang2 = pd.read_csv(
        "data/raw/clearglobal_language_use_gha_admin2.csv"
    )
    lang2.columns = lang2.columns.str.lower()
    lang2.to_sql(
        "language_admin2", engine,
        if_exists="replace", index=False
    )
    print(f"Language admin2 loaded: {len(lang2)}")
except FileNotFoundError:
    print("WARNING: language admin2 file not found")

if missing:
    raise RuntimeError(
        f"Load incomplete — missing tables: {', '.join(missing)}"
    )

print()
print("All data loaded successfully into MySQL.")