# tests/integration/test_daily_run.py

from run_daily import main


def test_daily_run_does_not_crash():
    """
    Full system integration test.
    Ensures daily run executes end-to-end without errors.
    """

    result = main(dry_run=True)

    assert result is not None
    assert isinstance(result, dict)
    assert result.get("status") in {"ok", "already_ran"}

