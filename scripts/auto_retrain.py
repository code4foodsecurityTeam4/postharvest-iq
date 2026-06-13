# Run: python -m scripts.auto_retrain  [--force]

import json
import os
import sys
from datetime import datetime, date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine
from app.ml.config import METADATA_PATH


def latest_real_data_date() -> date:
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT MAX(date) FROM wfp_prices WHERE priceflag != 'synthetic'"
        )).fetchone()
    return row[0] if row and row[0] else date(2020, 1, 1)


def last_retrain_date() -> date:
    try:
        with open(METADATA_PATH) as f:
            meta = json.load(f)
        raw = meta.get("last_retrain_date")
        if raw:
            return datetime.fromisoformat(raw).date()
    except FileNotFoundError:
        pass
    return date(2020, 1, 1)


def stamp_retrain():
    try:
        with open(METADATA_PATH) as f:
            meta = json.load(f)
    except FileNotFoundError:
        meta = {}
    meta["last_retrain_date"] = datetime.now().isoformat()
    with open(METADATA_PATH, "w") as f:
        json.dump(meta, f, indent=2)


def run(force: bool = False):
    latest  = latest_real_data_date()
    trained = last_retrain_date()

    print(f"Latest real data : {latest}")
    print(f"Last retrain     : {trained}")

    if not force and latest <= trained:
        print("No new data — skipping retrain.")
        return

    print("New data detected — retraining both models...")

    from app.ml.train_lstm import retrain as retrain_lstm
    retrain_lstm()

    from app.ml.train_xgboost import retrain as retrain_cls
    retrain_cls()

    stamp_retrain()
    print("Retrain complete.")


if __name__ == "__main__":
    force = "--force" in sys.argv
    run(force=force)
