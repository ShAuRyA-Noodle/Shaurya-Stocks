# tests/regression/test_equity_regression.py

import pandas as pd


EXPECTED_PATH = "tests/regression/data/expected_daily_snapshots.csv"
LATEST_PATH = "state/daily_snapshots.csv"


def test_equity_curve_regression_lock():
    """
    Prevent silent performance changes.
    Equity curve must remain identical unless explicitly updated.
    """

    expected = pd.read_csv(EXPECTED_PATH)
    latest = pd.read_csv(LATEST_PATH)

    # Compare only critical columns
    expected = expected[["date", "total_equity"]]
    latest = latest[["date", "total_equity"]]

    pd.testing.assert_frame_equal(
        expected.reset_index(drop=True),
        latest.reset_index(drop=True),
        check_exact=False,
        rtol=1e-6,
    )
