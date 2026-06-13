from app.ml.config import (
    STORE_THRESHOLD_PCT, STORAGE_MONTHS,
    TRANSPORT_COST_PER_KM, TRANSPORT_LAST_MILE_KM,
)

_DEFAULT_TRANSPORT = TRANSPORT_LAST_MILE_KM * TRANSPORT_COST_PER_KM  # 2.0 GHS


def calculate_net_return(
    current_price: float,
    forecast_price: float,
    quantity_bags: int,
    storage_cost_per_bag_month: float,
    storage_months: float = STORAGE_MONTHS,
    transport_cost_per_bag: float = _DEFAULT_TRANSPORT,
) -> dict:

    expected_gain  = forecast_price - current_price
    storage_cost   = storage_cost_per_bag_month * storage_months
    net_per_bag    = expected_gain - storage_cost - transport_cost_per_bag
    net_total      = net_per_bag * quantity_bags

    if net_per_bag > STORE_THRESHOLD_PCT * current_price:
        decision = "STORE"
    else:
        decision = "SELL_NOW"

    return {
        "decision":       decision,
        "expected_gain":  round(expected_gain, 2),
        "net_per_bag":    round(net_per_bag, 2),
        "net_total":      round(net_total, 2),
    }