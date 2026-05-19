import os
import pandas as pd
from sqlalchemy import create_engine

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL environment variable is required")

engine = create_engine(database_url)

# Load markets
markets = pd.read_csv("data/raw/wfp_markets_gha.csv")
markets.to_sql("wfp_markets", engine, if_exists="replace", index=False)
print(f"Markets loaded: {len(markets)}")

# Load prices
prices = pd.read_csv("data/raw/wfp_food_prices_gha.csv")
prices.to_sql("wfp_prices", engine, if_exists="replace", index=False)
print(f"Prices loaded: {len(prices)}")

print("All data loaded successfully into MySQL.")
