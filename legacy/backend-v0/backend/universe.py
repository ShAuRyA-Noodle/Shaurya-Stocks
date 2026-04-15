# backend/universe.py

"""
Defines the fixed equity universe used for all
cross-sectional modeling and portfolio decisions.

This file must remain stable to avoid data leakage
and survivorship bias.
"""

UNIVERSE = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
]

def get_universe() -> list[str]:
    """
    Returns the fixed equity universe.
    """
    return UNIVERSE.copy()
