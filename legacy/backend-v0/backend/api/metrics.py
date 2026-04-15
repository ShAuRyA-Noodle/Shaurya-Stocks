from fastapi import APIRouter, Depends
from backend.api.auth import require_api_key
from backend.state.portfolio import load_portfolio_state

from backend.monitoring.metrics import (
    load_equity_curve,
    compute_returns,
    compute_rolling_sharpe,
    compute_drawdown,
    compute_performance_summary,
)

router = APIRouter()


@router.get("/metrics")
def get_metrics(tier: str = Depends(require_api_key)):
    """
    Protected metrics endpoint.
    API key required. Tier not used yet.
    """
    df = load_equity_curve("state/daily_snapshots.csv")
    df = compute_returns(df)
    df = compute_rolling_sharpe(df)
    dd = compute_drawdown(df)
    summary = compute_performance_summary(df)

    return {
        "equity_curve": df[["date", "total_equity"]].to_dict(orient="records"),
        "drawdown": dd[["date", "drawdown"]].to_dict(orient="records"),
        "rolling_sharpe": df[["date", "rolling_sharpe"]].to_dict(orient="records"),
        "summary": summary,
    }

# backend/api/metrics.py
@router.get("/positions")
def get_positions():
    state = load_portfolio_state()

    if state is None:
        return {
            "positions": [],
            "cash": 0.0,
            "unrealized_pnl": 0.0,
        }

    return {
        "positions": list(state["positions"].values()),
        "cash": state["cash"],
        "unrealized_pnl": state["unrealized_pnl"],
    }
