from sqlalchemy.orm import Session
from app.services.strings import STRINGS, t
from app.services import ml_service, storage_service

CROPS = {
    "1": "Maize",
    "2": "Millet",
    "3": "Sorghum",
}

DISTRICTS = {
    "1": "Sagnarigu",
    "2": "Tolon",
    "3": "Kumbungu",
    "4": "Tamale",
}

DEFAULT_QTY = 20

# --- Demo mode -------------------------------------------------------------
# A normal farmer never types this. If the FIRST segment is "9", the session
# is in demo mode and the SECOND segment is a month (1-12) used to show how
# the recommendation changes across the season. Everything after that is the
# normal flow (language, crop, district, action). This keeps the real farmer
# menu completely clean — they only ever see 1/2/3 — while letting the
# presenter show June (SELL) vs October (STORE) live on the phone.
DEMO_PREFIX = "9"
# ---------------------------------------------------------------------------


def _fmt(n) -> str:
    """Whole cedis with a thousands separator: 2628.4 -> '2,628'."""
    try:
        return f"{round(float(n)):,}"
    except (TypeError, ValueError):
        return "0"


def handle_ussd_session(
    session_id: str,
    phone_number: str,
    text: str,
    db: Session,
) -> str:

    parts = [p for p in text.split("*") if p]

    # Detect and strip demo mode. If the first segment is the demo prefix,
    # the second segment is the override month; the rest is the normal flow.
    demo_month = None
    if parts and parts[0] == DEMO_PREFIX:
        if len(parts) >= 2 and parts[1].isdigit():
            m = int(parts[1])
            if 1 <= m <= 12:
                demo_month = m
        # remove the two demo segments so the rest is the normal flow
        parts = parts[2:]

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

    # Screen 1 — crop selection
    if level == 1:
        return (
            f"CON {t(lang, 'select_crop')}\n"
            f"1. {t(lang, 'maize')}\n"
            f"2. {t(lang, 'millet')}\n"
            f"3. {t(lang, 'sorghum')}"
        )

    # Screen 2 — district selection
    if level == 2:
        return (
            f"CON {t(lang, 'select_dist')}\n"
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
                quantity_bags=DEFAULT_QTY,
                language=lang,
                phone_number=phone_number,
                session_id=session_id,
                db=db,
                month=demo_month,
            )
            decision = (rec.get("decision") or "STORE").upper()
            net_total = rec.get("net_total", 0)
            gain_per_bag = round(
                rec.get("forecast_price", 0) - rec.get("current_price", 0)
            )

            menu = (
                "1. Find storage near me\n"
                "2. Sell all now\n"
                "3. Sell half store half\n"
                "4. Exit"
            )

            if decision == "STORE":
                body = (
                    f"CON {t(lang, 'store')}\n"
                    f"{t(lang, 'earn_per_bag').format(gain=_fmt(gain_per_bag))}\n"
                    f"{t(lang, 'total_for_bags').format(bags=DEFAULT_QTY, net=_fmt(net_total))}\n"
                    f"{t(lang, 'after_cost')}\n"
                )
            elif decision == "SELL_PARTIAL":
                body = (
                    f"CON {t(lang, 'sell_partial')}\n"
                    f"{t(lang, 'total_for_bags').format(bags=DEFAULT_QTY, net=_fmt(net_total))}\n"
                )
            else:  # SELL_NOW (or any unexpected value -> safe sell advice)
                body = (
                    f"CON {t(lang, 'sell_now')}\n"
                    f"{t(lang, 'sell_advice')}\n"
                )

            return body + menu

        except Exception:
            return f"END {t(lang, 'unavailable')}"

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
                        f"END {t(lang, 'nearest')}: {loc['name']}\n"
                        f"{loc['distance_km']:.1f} km\n"
                        f"{t(lang, 'cost_per_month').format(cost=loc['cost_per_bag'])}\n"
                        f"{t(lang, 'call')}: {loc['contact_number']}"
                    )
                return (
                    f"END {t(lang, 'no_storage')}\n"
                    f"{t(lang, 'consider_sell')}\n"
                    f"{t(lang, 'call_mofa')}"
                )
            except Exception:
                return f"END {t(lang, 'no_storage')}\n{t(lang, 'call_mofa')}"

        # Option 2 — sell all
        elif action == "2":
            try:
                market = storage_service.get_nearest_market(
                    district=district, db=db
                )
                rec = ml_service.get_recommendation(
                    crop=crop, district=district,
                    quantity_bags=DEFAULT_QTY, db=db, month=demo_month,
                )
                price = rec.get("current_price", 0)
                km_str = f"{market.get('distance_km', 0):.1f}"
                return (
                    f"END {t(lang, 'sell_now')}\n"
                    f"{t(lang, 'price_per_bag').format(price=_fmt(price))}\n"
                    f"{t(lang, 'market_label')}: {market.get('name', 'Tamale')}\n"
                    f"{t(lang, 'km_away').format(km=km_str)}"
                )
            except Exception:
                return f"END {t(lang, 'sell_now')}"

        # Option 3 — sell half store half
        elif action == "3":
            try:
                locations = storage_service.get_nearest_storage(
                    district=district, crop=crop, db=db
                )
                rec = ml_service.get_recommendation(
                    crop=crop, district=district,
                    quantity_bags=10, db=db, month=demo_month,
                )
                net = rec.get("net_total", 0)
                price = rec.get("current_price", 0)
                half = 10

                # If storing loses money (negative net), recommend selling
                # rather than showing a confusing negative "gain".
                if net <= 0:
                    return (
                        f"END {t(lang, 'sell_now')}\n"
                        f"{t(lang, 'sell_advice')}\n"
                        f"{t(lang, 'price_per_bag').format(price=_fmt(price))}"
                    )

                lines = [
                    f"END {t(lang, 'sell_partial')}",
                    t(lang, "sell_n_now").format(bags=half, amount=_fmt(price * half)),
                    t(lang, "store_n_est").format(bags=half, net=_fmt(net)),
                ]
                if locations:
                    loc = locations[0]
                    lines.append(f"{t(lang, 'nearest')}: {loc['name']}")
                    lines.append(f"{t(lang, 'call')}: {loc['contact_number']}")
                else:
                    lines.append(t(lang, "no_storage"))
                    lines.append(t(lang, "call_mofa"))
                return "\n".join(lines)
            except Exception:
                return f"END {t(lang, 'sell_partial')}"

        # Option 4 — exit
        else:
            return f"END {t(lang, 'thanks')}"

    return f"END {t(lang, 'invalid')}"