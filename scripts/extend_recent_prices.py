# Run: python -m scripts.extend_recent_prices
# To undo: DELETE FROM wfp_prices WHERE priceflag='synthetic';
#          DELETE FROM ghana_exchange_rates WHERE flag='synth';

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from sqlalchemy import text

from app.core.database import engine

SEED = 42

MARKETS     = ['Tamale', 'Bolga', 'Wa', 'Kumasi', 'Techiman']
COMMODITIES = ['Maize', 'Millet', 'Sorghum']

# harvest trough Oct-Dec, lean-season peak mid-year
SEASONAL = {
    1: 1.05, 2: 1.03, 3: 1.00, 4: 0.97, 5: 0.95,
    6: 0.92, 7: 0.90, 8: 0.93, 9: 0.96,
    10: 0.88, 11: 0.85, 12: 0.87,
}

MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']


def _drift(date: pd.Timestamp) -> float:
    if date.year <= 2024:
        return 1.022   # high food inflation / cedi depreciation era
    if date.year == 2025:
        return 0.997   # cedi recovery, prices easing
    return 1.002       # stable cedi, background inflation only (~2.4%/yr)


def _month_starts(after: pd.Timestamp, until: pd.Timestamp):
    start = (after + pd.offsets.MonthBegin(1)).normalize()
    return pd.date_range(start, until, freq='MS')


def extend_exchange_rates(conn, until: pd.Timestamp, rng) -> dict:
    """Fill missing monthly FX rows up to `until`; return {(year, month): rate}."""
    conn.execute(text("DELETE FROM ghana_exchange_rates WHERE flag = 'synth'"))

    rows = conn.execute(text("""
        SELECT year, months, value FROM ghana_exchange_rates
        WHERE element = 'Local currency units per USD'
          AND months != 'Annual value'
    """)).fetchall()
    fx = {(r[0], r[1]): float(r[2]) for r in rows}

    known = sorted(
        (pd.Timestamp(year=y, month=MONTH_NAMES.index(m) + 1, day=1), v)
        for (y, m), v in fx.items()
    )
    last_date, last_value = known[-1]

    n_filled = 0
    for date in _month_starts(last_date, until):
        value = round(last_value * (1 + rng.normal(0, 0.01)), 4)
        conn.execute(text("""
            INSERT INTO ghana_exchange_rates (iso3, area, year, months, element, value, flag)
            VALUES ('GHA', 'Ghana', :year, :months,
                    'Local currency units per USD', :value, 'synth')
        """), {"year": date.year, "months": MONTH_NAMES[date.month - 1], "value": value})
        fx[(date.year, MONTH_NAMES[date.month - 1])] = value
        last_value = value
        n_filled += 1

    print(f"Exchange rates: filled {n_filled} missing months (last real: {last_date:%Y-%m})")
    return fx


def extend_prices(conn, until: pd.Timestamp, fx: dict, rng):
    conn.execute(text("DELETE FROM wfp_prices WHERE priceflag = 'synthetic'"))

    total = 0
    for market in MARKETS:
        for commodity in COMMODITIES:
            anchor = conn.execute(text("""
                SELECT date, price, admin1, admin2, market_id, latitude, longitude,
                       category, commodity_id, unit, currency
                FROM wfp_prices
                WHERE market = :market AND commodity = :commodity
                  AND pricetype = 'Wholesale'
                ORDER BY date DESC
                LIMIT 1
            """), {"market": market, "commodity": commodity}).fetchone()
            if not anchor:
                continue

            last_date = pd.Timestamp(anchor[0])
            # strip the anchor month's seasonal factor to get the underlying level
            base  = float(anchor[1]) / SEASONAL[last_date.month]
            noise = 0.0

            n_series = 0
            for date in _month_starts(last_date, until):
                base  *= _drift(date)
                noise  = 0.7 * noise + rng.normal(0, 0.025)
                price  = round(base * SEASONAL[date.month] * (1 + noise), 2)

                rate     = fx.get((date.year, MONTH_NAMES[date.month - 1]))
                usdprice = round(price / rate, 4) if rate else None

                conn.execute(text("""
                    INSERT INTO wfp_prices
                        (date, admin1, admin2, market, market_id, latitude, longitude,
                         category, commodity, commodity_id, unit, priceflag, pricetype,
                         currency, price, usdprice)
                    VALUES
                        (:date, :admin1, :admin2, :market, :market_id, :lat, :lon,
                         :category, :commodity, :commodity_id, :unit, 'synthetic',
                         'Wholesale', :currency, :price, :usdprice)
                """), {
                    "date": date.replace(day=15).date(), "admin1": anchor[2],
                    "admin2": anchor[3], "market": market, "market_id": anchor[4],
                    "lat": anchor[5], "lon": anchor[6], "category": anchor[7],
                    "commodity": commodity, "commodity_id": anchor[8],
                    "unit": anchor[9], "currency": anchor[10],
                    "price": price, "usdprice": usdprice,
                })
                n_series += 1

            total += n_series
            print(f"  {market:<9} {commodity:<8} {last_date:%Y-%m} → {until:%Y-%m}  "
                  f"+{n_series} rows (anchor GHS {float(anchor[1]):.0f})")

    print(f"\nInserted {total} synthetic price rows.")


def run():
    rng   = np.random.RandomState(SEED)
    until = pd.Timestamp.today().normalize().replace(day=1)

    with engine.begin() as conn:
        fx = extend_exchange_rates(conn, until, rng)
        extend_prices(conn, until, fx, rng)

    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT MIN(date), MAX(date), COUNT(*) FROM wfp_prices
            WHERE priceflag = 'synthetic'
        """)).fetchone()
        print(f"Synthetic span: {row[0]} → {row[1]}  ({row[2]} rows)")


if __name__ == "__main__":
    run()
