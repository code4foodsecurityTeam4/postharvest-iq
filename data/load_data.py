import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME = (
    os.environ[k] for k in ['DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'DB_NAME']
)

engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Load markets
markets = pd.read_csv("data/raw/wfp_markets_gha.csv")
markets.columns = markets.columns.str.lower()
markets.to_sql("wfp_markets", engine, if_exists="replace", index=False)
print(f"Markets loaded: {len(markets)}")

# Load prices
prices = pd.read_csv("data/raw/wfp_food_prices_gha.csv")
prices.columns = prices.columns.str.lower()
prices.to_sql("wfp_prices", engine, if_exists="replace", index=False)
print(f"Prices loaded: {len(prices)}")

# Load exchange rates
try:
    fx = pd.read_csv("data/raw/ghana_exchange_rates.csv")
    fx.columns = fx.columns.str.lower()
    fx.to_sql("ghana_exchange_rates", engine, if_exists="replace", index=False)
    print(f"Exchange rates loaded: {len(fx)}")
except FileNotFoundError:
    print("ghana_exchange_rates.csv not found")

# Load producer prices
try:
    producer = pd.read_csv("data/raw/ghana_producer_prices.csv")
    producer.columns = producer.columns.str.lower()
    producer.to_sql("fao_producer_prices", engine, if_exists="replace", index=False)
    print(f"Producer prices loaded: {len(producer)}")
except FileNotFoundError:
    print("ghana_producer_prices.csv not found")

print("All data loaded successfully into MySQL.")
