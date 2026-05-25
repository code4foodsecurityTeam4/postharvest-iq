"""
Seed script for verified GCX warehouse locations.
Run once to populate the storage_locations table in your local DB.

Usage:
    python scripts/seed_storage_locations.py
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

from app.core.database import engine

GCX_WAREHOUSES = [
    {
        "name": "GCX Tamale Warehouse",
        "type": "Ghana Commodity Exchange",
        "region": "Northern",
        "district": "Tamale",
        "gps_lat": 9.4034,
        "gps_lng": -0.8424,
        "cost_per_bag_per_month": 0.80,
        "min_bags": 20,
        "max_bags": 9999,
        "crops_accepted": "Maize,Sorghum",
        "contact_number": "0504774779",
        "verified": True,
        "is_active": True,
    },
    {
        "name": "GCX Sandema Warehouse",
        "type": "Ghana Commodity Exchange",
        "region": "Upper East",
        "district": "Sandema",
        "gps_lat": 10.8566,
        "gps_lng": -1.2553,
        "cost_per_bag_per_month": 0.80,
        "min_bags": 20,
        "max_bags": 9999,
        "crops_accepted": "Maize,Sorghum",
        "contact_number": "0594164451",
        "verified": True,
        "is_active": True,
    },
    {
        "name": "GCX Wa Warehouse",
        "type": "Ghana Commodity Exchange",
        "region": "Upper West",
        "district": "Wa",
        "gps_lat": 10.0601,
        "gps_lng": -2.5099,
        "cost_per_bag_per_month": 0.80,
        "min_bags": 20,
        "max_bags": 9999,
        "crops_accepted": "Maize,Sorghum",
        "contact_number": "0593864997",
        "verified": True,
        "is_active": True,
    },
    {
        "name": "GCX Tumu Warehouse",
        "type": "Ghana Commodity Exchange",
        "region": "Upper West",
        "district": "Tumu",
        "gps_lat": 10.9000,
        "gps_lng": -1.9833,
        "cost_per_bag_per_month": 0.80,
        "min_bags": 20,
        "max_bags": 9999,
        "crops_accepted": "Maize,Sorghum",
        "contact_number": "0594164424",
        "verified": True,
        "is_active": True,
    },
    {
        "name": "GCX Bolga Warehouse",
        "type": "Ghana Commodity Exchange",
        "region": "Upper East",
        "district": "Bolga",
        "gps_lat": 10.7833,
        "gps_lng": -0.8500,
        "cost_per_bag_per_month": 0.80,
        "min_bags": 20,
        "max_bags": 9999,
        "crops_accepted": "Maize,Sorghum",
        "contact_number": "0504444065",
        "verified": True,
        "is_active": True,
    },
]


def seed():
    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT COUNT(*) FROM storage_locations WHERE type = 'Ghana Commodity Exchange'")
        ).scalar()

        if existing:
            print(f"Skipping — {existing} GCX warehouse(s) already in DB.")
            return

        conn.execute(
            text("""
                INSERT INTO storage_locations
                    (name, type, region, district, gps_lat, gps_lng,
                     cost_per_bag_per_month, min_bags, max_bags,
                     crops_accepted, contact_number, verified, is_active)
                VALUES
                    (:name, :type, :region, :district, :gps_lat, :gps_lng,
                     :cost_per_bag_per_month, :min_bags, :max_bags,
                     :crops_accepted, :contact_number, :verified, :is_active)
            """),
            GCX_WAREHOUSES,
        )
        conn.commit()

    print(f"Loaded {len(GCX_WAREHOUSES)} verified GCX warehouse locations.")
    for w in GCX_WAREHOUSES:
        print(f"  - {w['name']} ({w['district']}) | GHS {w['cost_per_bag_per_month']}/bag/month | {w['contact_number']}")


if __name__ == "__main__":
    seed()
