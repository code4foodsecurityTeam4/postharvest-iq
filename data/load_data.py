import pandas as pd
from sqlalchemy import create_engine

engine = create_engine(
    "mysql+pymysql://root:postharvest2026@127.0.0.1:3306/postharvest_iq"
)

# Load markets
markets = pd.read_csv("data/raw/wfp_markets_gha.csv")
markets.to_sql("wfp_markets", engine, if_exists="replace", index=False)
print(f"Markets loaded: {len(markets)}")

# Load prices
prices = pd.read_csv("data/raw/wfp_food_prices_gha.csv")
prices.to_sql("wfp_prices", engine, if_exists="replace", index=False)
print(f"Prices loaded: {len(prices)}")

print("All data loaded successfully into MySQL.")
