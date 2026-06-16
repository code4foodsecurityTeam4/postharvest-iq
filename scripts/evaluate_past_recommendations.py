"""
Post-hoc feedback loop: score past STORE/SELL_NOW recommendations against actuals.

For every recommendation logged ~3 months ago, this script looks up the actual
observed wholesale price in wfp_prices at recommendation_date + FORECAST_HORIZON_MONTHS
(±15-day window to handle month-end date alignment) and re-evaluates whether the
model's decision was economically correct given what actually happened.

Correctness criterion
    Uses the same net return formula as recommendation_service.calculate_net_return:
        net = (actual_price - current_price) - storage_cost - transport_cost
        Correct if: (decision == STORE and net > threshold) or
                    (decision == SELL_NOW and net <= threshold)

Limitations
    - Requires real WFP price data to exist at t+3. Synthetic rows are not used
      for evaluation because they do not represent actual market outcomes.
    - The ±15-day window averages available prices near the target date; thin
      markets with sparse data may return NULL and be skipped.
    - Accuracy here measures economic correctness of the binary decision, not
      forecast accuracy. A correct STORE that earned only GHS 1 counts the same
      as one that earned GHS 300.
"""

# Run: python -m scripts.evaluate_past_recommendations

import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine
from app.ml.config import (
    FORECAST_HORIZON_MONTHS, STORE_THRESHOLD_PCT,
    STORAGE_COST_PER_BAG_MONTH, STORAGE_MONTHS,
    TRANSPORT_COST_PER_KM, TRANSPORT_LAST_MILE_KM,
)

MARKET_FOR_DISTRICT = {
    "Tamale":     "Tamale",
    "Bolgatanga": "Bolga",
    "Wa":         "Wa",
}

_TRANSPORT = TRANSPORT_LAST_MILE_KM * TRANSPORT_COST_PER_KM


def run():
    cutoff_start = datetime.now() - timedelta(days=FORECAST_HORIZON_MONTHS * 31 + 14)
    cutoff_end   = datetime.now() - timedelta(days=FORECAST_HORIZON_MONTHS * 28)

    with engine.connect() as conn:
        recs = conn.execute(text("""
            SELECT id, crop, district, decision, current_price, forecast_price,
                   quantity_bags, created_at
            FROM recommendations
            WHERE created_at BETWEEN :start AND :end
            ORDER BY created_at
        """), {"start": cutoff_start, "end": cutoff_end}).fetchall()

    if not recs:
        print(f"No recommendations found between {cutoff_start.date()} and {cutoff_end.date()}.")
        return

    total = correct = 0
    rows = []

    with engine.connect() as conn:
        for rec in recs:
            rec_id, crop, district, decision, current_price, forecast_price, _, created_at = rec
            market = MARKET_FOR_DISTRICT.get(district, "Tamale")

            actual_row = conn.execute(text("""
                SELECT AVG(price) FROM wfp_prices
                WHERE commodity = :crop
                  AND market    = :market
                  AND pricetype = 'Wholesale'
                  AND date BETWEEN DATE_ADD(:dt, INTERVAL :h MONTH) - INTERVAL 15 DAY
                          AND     DATE_ADD(:dt, INTERVAL :h MONTH) + INTERVAL 15 DAY
            """), {
                "crop": crop, "market": market,
                "dt": created_at, "h": FORECAST_HORIZON_MONTHS,
            }).fetchone()

            actual_price = float(actual_row[0]) if actual_row and actual_row[0] else None
            if actual_price is None:
                continue

            net = (actual_price - current_price
                   - STORAGE_COST_PER_BAG_MONTH * STORAGE_MONTHS
                   - _TRANSPORT)
            should_have_stored = net > STORE_THRESHOLD_PCT * current_price
            was_correct = (
                (decision == "STORE"    and should_have_stored) or
                (decision == "SELL_NOW" and not should_have_stored)
            )

            total   += 1
            correct += int(was_correct)
            rows.append({
                "id":           rec_id,
                "date":         created_at.date(),
                "crop":         crop,
                "district":     district,
                "decision":     decision,
                "current":      round(current_price, 0),
                "forecast":     round(forecast_price, 0),
                "actual":       round(actual_price, 0),
                "net_if_stored": round(net, 2),
                "correct":      "✓" if was_correct else "✗",
            })

    if not rows:
        print("Actual prices not yet available for the evaluation window.")
        return

    print(f"\nRecommendation outcome report  ({cutoff_start.date()} → {cutoff_end.date()})")
    print(f"{'ID':>4}  {'Date':<11} {'Crop':<8} {'District':<12} {'Decision':<9} "
          f"{'Current':>8} {'Forecast':>9} {'Actual':>8} {'Net':>8}  OK")
    print("-" * 88)
    for r in rows:
        print(f"{r['id']:>4}  {str(r['date']):<11} {r['crop']:<8} {r['district']:<12} "
              f"{r['decision']:<9} {r['current']:>8.0f} {r['forecast']:>9.0f} "
              f"{r['actual']:>8.0f} {r['net_if_stored']:>8.2f}  {r['correct']}")

    pct = 100 * correct / total
    print(f"\nAccuracy: {correct}/{total} = {pct:.1f}%")
    print("(Correct = model's STORE/SELL_NOW matched what the actual price justified)")


if __name__ == "__main__":
    run()
