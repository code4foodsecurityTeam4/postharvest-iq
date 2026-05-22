# run from project root: python -m data.load_data
from pathlib import Path
import pandas as pd
from app.core.database import Base, engine
from app.models.wfp_market import WFPMarket          # noqa: F401 — registers table with Base
from app.models.wfp_price import WFPPrice            # noqa: F401 — registers table with Base
from app.models.exchange_rate import ExchangeRate    # noqa: F401 — registers table with Base
from app.models.producer_price import ProducerPrice  # noqa: F401 — registers table with Base

FX_COLS = ["iso3", "area", "year", "months", "element", "value", "flag"]
PP_COLS = ["iso3", "area", "item", "element", "year", "months", "unit", "value", "flag"]

REQUIRED_CSVS = [
    "data/raw/wfp_markets_gha.csv",
    "data/raw/wfp_food_prices_gha.csv",
    "data/raw/ghana_exchange_rates.csv",
    "data/raw/ghana_producer_prices.csv",
]


def main():
    missing = [p for p in REQUIRED_CSVS if not Path(p).exists()]
    if missing:
        raise FileNotFoundError(
            "Required CSV files not found — aborting before any DB changes:\n"
            + "\n".join(f"  {p}" for p in missing)
        )

    # Drop and recreate only the raw-data tables loaded from CSV.
    # Application tables (storage_locations, recommendations, price_forecasts)
    # are populated at runtime by the API and must not be touched here.
    # Language tables have no ORM model and use if_exists='replace' below.
    # Drop child tables before parents to satisfy FK constraints:
    # wfp_prices has a FK to wfp_markets, so it must be dropped first.
    for table in [
        WFPPrice.__table__,
        WFPMarket.__table__,
        ExchangeRate.__table__,
        ProducerPrice.__table__,
    ]:
        table.drop(engine, checkfirst=True)

    Base.metadata.create_all(engine, tables=[
        WFPMarket.__table__,
        WFPPrice.__table__,
        ExchangeRate.__table__,
        ProducerPrice.__table__,
    ])

    markets = pd.read_csv("data/raw/wfp_markets_gha.csv")
    markets.columns = markets.columns.str.lower()
    markets.to_sql("wfp_markets", engine, if_exists="append", index=False)
    print(f"Markets loaded: {len(markets)}")

    prices = pd.read_csv("data/raw/wfp_food_prices_gha.csv")
    prices.columns = prices.columns.str.lower()
    prices.to_sql("wfp_prices", engine, if_exists="append", index=False)
    print(f"Prices loaded: {len(prices)}")

    fx = pd.read_csv("data/raw/ghana_exchange_rates.csv")
    fx.columns = fx.columns.str.lower()
    fx[FX_COLS].to_sql("ghana_exchange_rates", engine, if_exists="append", index=False)
    print(f"Exchange rates loaded: {len(fx)}")

    producer = pd.read_csv("data/raw/ghana_producer_prices.csv")
    producer.columns = producer.columns.str.lower()
    producer[PP_COLS].to_sql("fao_producer_prices", engine, if_exists="append", index=False)
    print(f"Producer prices loaded: {len(producer)}")

    try:
        lang1 = pd.read_csv("data/raw/clearglobal_language_use_gha_admin1.csv")
        lang1.columns = lang1.columns.str.lower()
        lang1.to_sql("language_admin1", engine, if_exists="replace", index=False)
        print(f"Language admin1 loaded: {len(lang1)}")
    except FileNotFoundError:
        print("WARNING: language admin1 file not found")

    try:
        lang2 = pd.read_csv("data/raw/clearglobal_language_use_gha_admin2.csv")
        lang2.columns = lang2.columns.str.lower()
        lang2.to_sql("language_admin2", engine, if_exists="replace", index=False)
        print(f"Language admin2 loaded: {len(lang2)}")
    except FileNotFoundError:
        print("WARNING: language admin2 file not found")

    print()
    print("All data loaded successfully into MySQL.")


if __name__ == "__main__":
    main()
