import logging
from sqlalchemy.orm import Session
from app.services.strings import t
from app.services import ml_service, storage_service

_log = logging.getLogger(__name__)

CROPS = {
    "1": "Maize",
    "2": "Millet",
    "3": "Sorghum",
}

DISTRICTS = {
    "1": "Tamale",
    "2": "Bolgatanga",
    "3": "Wa",
}

DEFAULT_QTY = 20

# prefix "9" enters demo mode: second segment is the override month (1-12),
# then the normal flow continues — farmers never see this path
DEMO_PREFIX = "9"


def _fmt(n) -> str:
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

    demo_month = None
    if parts and parts[0] == DEMO_PREFIX:
        if len(parts) >= 2 and parts[1].isdigit():
            m = int(parts[1])
            if 1 <= m <= 12:
                demo_month = m
        parts = parts[2:]

    level = len(parts)

    if level == 0:
        return (
            "CON Welcome to PostHarvest IQ\n"
            "1. English\n"
            "2. Dagbani\n"
            "3. Hausa"
        )

    lang_map = {"1": "en", "2": "dag", "3": "hau"}
    lang = lang_map.get(parts[0], "en")

    if level == 1:
        return (
            f"CON {t(lang, 'select_crop')}\n"
            f"1. {t(lang, 'maize')}\n"
            f"2. {t(lang, 'millet')}\n"
            f"3. {t(lang, 'sorghum')}"
        )

    if level == 2:
        return (
            f"CON {t(lang, 'select_dist')}\n"
            "1. Tamale\n"
            "2. Bolgatanga\n"
            "3. Wa"
        )

    if level == 3:
        return f"CON {t(lang, 'enter_bags')}"

    bags = DEFAULT_QTY
    if level >= 4:
        if not parts[3].isdigit() or int(parts[3]) < 1:
            return f"END {t(lang, 'invalid')}"
        bags = min(int(parts[3]), 999)

    if level == 4:
        crop = CROPS.get(parts[1], "Maize")
        district = DISTRICTS.get(parts[2], "Tamale")

        try:
            rec = ml_service.get_recommendation(
                crop=crop,
                district=district,
                quantity_bags=bags,
                language=lang,
                phone_number=phone_number,
                session_id=session_id,
                db=db,
                month=demo_month,
            )
            decision = (rec.get("decision") or "STORE").upper()
            net_total    = rec.get("net_total", 0)
            gain_per_bag = round(rec.get("net_per_bag", 0))
            fcast_low  = rec.get("forecast_low")
            fcast_high = rec.get("forecast_high")

            menu = (
                f"1. {t(lang, 'menu_find_storage')}\n"
                f"2. {t(lang, 'menu_sell_all')}\n"
                f"3. {t(lang, 'menu_sell_half')}\n"
                f"4. {t(lang, 'menu_exit')}"
            )

            current_price = rec.get("current_price", 0)

            if decision == "STORE":
                range_line = ""
                if fcast_low and fcast_high:
                    range_line = (
                        t(lang, "forecast_range").format(
                            low=_fmt(fcast_low), high=_fmt(fcast_high)
                        ) + "\n"
                    )
                body = (
                    f"CON {t(lang, 'store')}\n"
                    f"{t(lang, 'price_today').format(price=_fmt(current_price))}\n"
                    f"{range_line}"
                    f"{t(lang, 'earn_per_bag').format(gain=_fmt(gain_per_bag))}\n"
                    f"{t(lang, 'total_for_bags').format(bags=bags, net=_fmt(net_total))}\n"
                )
            else:
                body = (
                    f"CON {t(lang, 'sell_now')}\n"
                    f"{t(lang, 'sell_now_price').format(price=_fmt(current_price))}\n"
                    f"{t(lang, 'sell_now_total').format(bags=bags, total=_fmt(current_price * bags))}\n"
                )

            return body + menu

        except Exception:
            _log.exception("level-4 recommendation failed sid=%s", session_id)
            return f"END {t(lang, 'unavailable')}"

    if level == 5:
        crop = CROPS.get(parts[1], "Maize")
        district = DISTRICTS.get(parts[2], "Tamale")
        action = parts[4]

        if action == "1":
            try:
                locations = storage_service.get_nearest_storage(
                    district=district, crop=crop, db=db
                )
                if locations:
                    loc = locations[0]
                    town = loc.get("district", district)
                    km = f"{loc['distance_km']:.1f}"
                    cost = f"{float(loc['cost_per_bag']):.2f}"
                    return (
                        f"END {t(lang, 'nearest')}: {loc['name']}\n"
                        f"{t(lang, 'store_location').format(town=town, km=km)}\n"
                        f"{t(lang, 'cost_per_month').format(cost=cost)}\n"
                        f"{t(lang, 'call')}: {loc['contact_number']}"
                    )
                return (
                    f"END {t(lang, 'no_storage')}\n"
                    f"{t(lang, 'consider_sell')}\n"
                    f"{t(lang, 'call_mofa')}"
                )
            except Exception:
                _log.exception("storage lookup failed sid=%s", session_id)
                return f"END {t(lang, 'no_storage')}\n{t(lang, 'call_mofa')}"

        elif action == "2":
            try:
                market = storage_service.get_nearest_market(
                    district=district, db=db
                )
                town = market.get("name", "Tamale")
                return (
                    f"END {t(lang, 'sell_now')}\n"
                    f"{t(lang, 'nearest_market').format(town=town)}"
                )
            except Exception:
                _log.exception("market lookup failed sid=%s", session_id)
                return f"END {t(lang, 'sell_now')}"

        elif action == "3":
            try:
                half = max(bags // 2, 1)
                locations = storage_service.get_nearest_storage(
                    district=district, crop=crop, db=db
                )
                rec = ml_service.get_recommendation(
                    crop=crop, district=district,
                    quantity_bags=half, db=db, month=demo_month,
                    phone_number=phone_number, session_id=session_id,
                )
                net = rec.get("net_total", 0)
                price = rec.get("current_price", 0)

                if net <= 0:
                    return (
                        f"END {t(lang, 'sell_now')}\n"
                        f"{t(lang, 'sell_advice')}\n"
                        f"{t(lang, 'price_today').format(price=_fmt(price))}"
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
                _log.exception("sell-half flow failed sid=%s", session_id)
                return f"END {t(lang, 'sell_partial')}"

        else:
            return f"END {t(lang, 'thanks')}"

    return f"END {t(lang, 'invalid')}"