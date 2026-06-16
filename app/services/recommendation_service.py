"""
Economic return calculation for the storage decision.

No ML — pure arithmetic on the LSTM's price forecast.

The STORE threshold is relative (STORE_THRESHOLD_PCT = 5 % of current price)
to remain scale-invariant across Ghana's cedi depreciation eras. A fixed GHS 20
net gain threshold meant something when bags were GHS 200 (2015). By 2025 at
GHS 1,000 per bag, the same GHS 20 threshold would label almost everything STORE,
even when the real return is negligible. 5 % of the current price requires
proportionally more gain as prices rise, preserving the same economic meaning.
"""

from app.ml.config import (
    STORE_THRESHOLD_PCT, STORAGE_MONTHS,
    TRANSPORT_COST_PER_KM, TRANSPORT_LAST_MILE_KM,
)

_DEFAULT_TRANSPORT = TRANSPORT_LAST_MILE_KM * TRANSPORT_COST_PER_KM


def calculate_net_return(
    current_price: float,
    forecast_price: float,
    quantity_bags: int,
    storage_cost_per_bag_month: float,
    storage_months: float = STORAGE_MONTHS,
    transport_cost_per_bag: float = _DEFAULT_TRANSPORT,
) -> dict:
    """
    Compute the net economic return from storing for 3 months vs selling today.

    Formula (per bag):
        expected_gain  = forecast_price − current_price
        storage_cost   = storage_cost_per_bag_month × storage_months
        net_per_bag    = expected_gain − storage_cost − transport_cost_per_bag
        decision       = STORE if net_per_bag > STORE_THRESHOLD_PCT × current_price

    Args:
        current_price:              latest wholesale price (GHS / 100-kg bag)
        forecast_price:             LSTM price forecast 3 months ahead (GHS / bag)
        quantity_bags:              number of bags the farmer holds
        storage_cost_per_bag_month: GCX warehouse rate; passed in from ml_service
                                    so the caller controls the cost assumption
        storage_months:             holding period (default 3.0 from config)
        transport_cost_per_bag:     Haversine-derived freight; defaults to
                                    10 km last-mile × 0.20 GHS/km when GPS is
                                    unavailable

    Returns:
        dict with keys: decision, expected_gain, net_per_bag, net_total (GHS)
    """

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