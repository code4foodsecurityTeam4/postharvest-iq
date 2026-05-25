from sqlalchemy.orm import Session
from app.services.strings import STRINGS
from app.services import ml_service, storage_service

CROPS = {
    "1": "Maize",
    "2": "Millet",
    "3": "Sorghum"
}

DISTRICTS = {
    "1": "Sagnarigu",
    "2": "Tolon",
    "3": "Kumbungu",
    "4": "Tamale"
}

def handle_ussd_session(
    session_id: str,
    phone_number: str,
    text: str,
    db: Session
) -> str:

    parts = [p for p in text.split("*") if p]
    level = len(parts)

    # Screen 0 — language selection
    if level == 0:
        return (
            "CON Welcome to PostHarvest IQ\n"
            "1. English\n"
            "2. Dagbani\n"
            "3. Hausa"
        )

    lang_map = {"1": "en", "2": "dag", "3": "hau"}
    lang = lang_map.get(parts[0], "en")
    s = STRINGS[lang]

    # Screen 1 — crop selection
    if level == 1:
        return (
            f"CON {s['select_crop']}\n"
            f"1. {s['maize']}\n"
            f"2. Millet\n"
            f"3. Sorghum"
        )

    # Screen 2 — district selection
    if level == 2:
        return (
            f"CON {s['select_dist']}\n"
            "1. Sagnarigu\n"
            "2. Tolon\n"
            "3. Kumbungu\n"
            "4. Tamale"
        )

    # Screen 3 — recommendation
    if level == 3:
        crop = CROPS.get(parts[1], "Maize")
        district = DISTRICTS.get(parts[2], "Tamale")

        try:
            rec = ml_service.get_recommendation(
                crop=crop,
                district=district,
                quantity_bags=20,
                language=lang,
                phone_number=phone_number,
                session_id=session_id,
                db=db
            )
            decision = rec.get("decision", "STORE")
            net_total = rec.get("net_total", 0)
            forecast_price = rec.get("forecast_price", 0)
            current_price = rec.get("current_price", 0)
            gain_per_bag = round(forecast_price - current_price, 2)

            return (
                f"CON {s[decision.lower().replace('_now','_now').replace('sell_now','sell_now')]}\n"
                f"+GHS {gain_per_bag}/bag\n"
               f"Net: GHS {net_total}\n"
                "1. Find storage near me\n"
                "2. Sell all now\n"
                "3. Sell half store half\n"
                "4. Exit"
            )
        except Exception as e:
            return f"END Service temporarily unavailable. Try again shortly."

    # Screen 4 — action
    if level == 4:
        crop = CROPS.get(parts[1], "Maize")
        district = DISTRICTS.get(parts[2], "Tamale")
        action = parts[3]

        # Option 1 — find storage
        if action == "1":
            try:
                locations = storage_service.get_nearest_storage(
                    district=district, crop=crop, db=db
                )
                if locations:
                    loc = locations[0]
                    return (
                        f"END {s['nearest']}: {loc['name']}\n"
                        f"{loc['distance_km']:.1f}km\n"
                        f"GHS {loc['cost_per_bag']}/bag/mo\n"
                        f"{s['call']}: {loc['contact_number']}"
                    )
                return "END No verified storage found nearby. Call MoFA: 118"
            except Exception:
                return "END Storage lookup unavailable. Call MoFA: 118"

        # Option 2 — sell all
        elif action == "2":
            try:
                market = storage_service.get_nearest_market(
                    district=district, db=db
                )
                rec = ml_service.get_recommendation(
                    crop=crop, district=district,
                    quantity_bags=20, db=db
                )
                price = rec.get("current_price", 0)
                return (
                    f"END {s['sell_now']}\n"
                    f"Price: GHS {price}/bag\n"
                    f"Market: {market.get('name','Tamale')}\n"
                    f"{market.get('distance_km',0):.1f}km away"
                )
            except Exception:
                return "END Sell at your nearest market today."

        # Option 3 — sell half store half
        elif action == "3":
            try:
                locations = storage_service.get_nearest_storage(
                    district=district, crop=crop, db=db
                )
                rec = ml_service.get_recommendation(
                    crop=crop, district=district,
                    quantity_bags=10, db=db
                )
                net = rec.get("net_total", 0)
                price = rec.get("current_price", 0)
                loc = locations[0] if locations else {}
                return (
                    f"END {s['sell_partial']}\n"
                    f"Sell 10 bags: GHS {price*10:.0f} now\n"
                    f"Store 10 bags: Est +GHS {net:.0f}\n"
                    f"Storage: {loc.get('name','')}\n"
                    f"{s['call']}: {loc.get('contact_number','118')}"
                )
            except Exception:
                return "END Sell half now. Store half at nearest warehouse."

        # Option 4 — exit
        else:
            return "END Thank you for using PostHarvest IQ."

    return "END Invalid input. Please try again."