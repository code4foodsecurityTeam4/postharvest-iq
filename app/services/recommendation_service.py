from app.ml.config import STORE_THRESHOLD, PARTIAL_THRESHOLD


def calculate_net_return(
    current_price: float,
    forecast_price: float,
    quantity_bags: int,
    storage_cost_per_bag_month: float,
    storage_months: float = 1.5,
    transport_cost_per_bag: float = 2.0
) -> dict:

    expected_gain  = forecast_price - current_price
    storage_cost   = storage_cost_per_bag_month * storage_months
    net_per_bag    = expected_gain - storage_cost - transport_cost_per_bag
    net_total      = net_per_bag * quantity_bags

    if net_per_bag > STORE_THRESHOLD:
        decision = "STORE"
    elif net_per_bag > PARTIAL_THRESHOLD:
        decision = "SELL_PARTIAL"
    else:
        decision = "SELL_NOW"

    return {
        "decision":       decision,
        "expected_gain":  round(expected_gain, 2),
        "net_per_bag":    round(net_per_bag, 2),
        "net_total":      round(net_total, 2),
    }