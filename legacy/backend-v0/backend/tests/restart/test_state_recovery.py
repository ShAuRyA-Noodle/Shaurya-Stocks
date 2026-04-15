import json
from backend.state.portfolio import initialize_portfolio_state
from run_daily import main


def test_state_recovery_is_idempotent(tmp_path):
    """
    If the system crashes and restarts,
    re-running the same day must NOT duplicate trades.
    """

    # First run
    result1 = main(dry_run=False)
    assert result1["status"] in ("ok", "already_ran")

    # Simulate restart (reload state)
    state_after_first = initialize_portfolio_state()

    # Second run (same day)
    result2 = main(dry_run=False)
    assert result2["status"] == "already_ran"

    # Reload state again
    state_after_second = initialize_portfolio_state()

    # State must be identical
    assert state_after_first == state_after_second
