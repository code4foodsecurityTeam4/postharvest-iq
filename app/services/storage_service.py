import math
from sqlalchemy.orm import Session
from app.models.storage import StorageLocation
from app.models.wfp_market import WFPMarket

DISTRICT_COORDS = {
    "Tamale":     (9.40,  -0.84),
    "Bolgatanga": (10.79, -0.85),
    "Wa":         (10.06, -2.51),
}

DISTRICT_TO_MARKET = {
    "Tamale":     "Tamale",
    "Bolgatanga": "Bolga",
    "Wa":         "Wa",
}

def haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlng/2)**2)
    return R * 2 * math.asin(math.sqrt(a))

def get_nearest_storage(
    district: str,
    crop: str,
    db: Session,
    limit: int = 3
) -> list:
    coords = DISTRICT_COORDS.get(district, (9.40, -0.83))
    dist_lat, dist_lng = coords

    locations = db.query(StorageLocation).filter(
        StorageLocation.verified == True,
        StorageLocation.is_active == True,
        StorageLocation.crops_accepted.contains(crop)
    ).all()

    results = []
    for loc in locations:
        dist = haversine_km(
            dist_lat, dist_lng,
            loc.gps_lat, loc.gps_lng
        )
        results.append({
            "id":             loc.id,
            "name":           loc.name,
            "distance_km":    round(dist, 2),
            "cost_per_bag":   loc.cost_per_bag_per_month,
            "contact_number": loc.contact_number,
            "type":           loc.type,
            "district":       loc.district,
        })

    results.sort(key=lambda x: x["distance_km"])
    return results[:limit]

def get_nearest_market(district: str, db: Session) -> dict:
    market_name = DISTRICT_TO_MARKET.get(district, "Tamale")
    coords = DISTRICT_COORDS.get(district, (9.40, -0.83))

    market = db.query(WFPMarket).filter(
        WFPMarket.market == market_name
    ).first()

    if not market:
        return {"name": market_name, "distance_km": 0}

    dist = haversine_km(
        coords[0], coords[1],
        market.latitude, market.longitude
    )
    return {
        "name":        market.market,
        "distance_km": round(dist, 2),
        "latitude":    market.latitude,
        "longitude":   market.longitude,
    }