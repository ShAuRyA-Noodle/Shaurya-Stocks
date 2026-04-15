import math


def compute_position_size(
    cash: float,
    price: float,
    risk_fraction: float = 0.10,
) -> int:
    """
    Compute position size based on available cash and price.
    Conservative, no leverage.
    """
    if price <= 0:
        return 0

    risk_cash = cash * risk_fraction
    quantity = math.floor(risk_cash / price)

    return max(quantity, 0)
