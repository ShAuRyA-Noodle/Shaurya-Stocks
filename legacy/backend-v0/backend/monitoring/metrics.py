import pandas as pd


def load_equity_curve(snapshot_path: str) -> pd.DataFrame:
    """
    Load daily snapshots and return equity curve DataFrame.
    """
    df = pd.read_csv(snapshot_path, parse_dates=["date"])
    df = df.sort_values("date")

    if "total_equity" not in df.columns:
        raise KeyError("total_equity column missing from snapshots")

    return df[["date", "total_equity"]]
def compute_drawdown(equity_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute drawdown from equity curve.
    """
    df = equity_df.copy()
    df["peak"] = df["total_equity"].cummax()
    df["drawdown"] = (df["total_equity"] - df["peak"]) / df["peak"]

    return df
def compute_returns(equity_df):
    """
    Compute daily returns from equity curve.
    """
    df = equity_df.copy()
    df["return"] = df["total_equity"].pct_change().fillna(0.0)
    return df
import numpy as np

def compute_rolling_sharpe(returns_df, window=20, trading_days=252):
    """
    Compute rolling Sharpe ratio.
    """
    df = returns_df.copy()

    rolling_mean = df["return"].rolling(window).mean()
    rolling_std = df["return"].rolling(window).std()

    sharpe = np.sqrt(trading_days) * (rolling_mean / rolling_std)

    df["rolling_sharpe"] = sharpe.replace([np.inf, -np.inf], 0.0).fillna(0.0)

    return df
def compute_performance_summary(equity_df):
    """
    Compute high-level performance metrics.
    """
    start_equity = equity_df["total_equity"].iloc[0]
    end_equity = equity_df["total_equity"].iloc[-1]

    num_days = (equity_df["date"].iloc[-1] - equity_df["date"].iloc[0]).days
    years = max(num_days / 365.25, 1e-6)

    cagr = (end_equity / start_equity) ** (1 / years) - 1

    drawdown_df = compute_drawdown(equity_df)
    max_drawdown = drawdown_df["drawdown"].min()

    return {
        "start_equity": float(start_equity),
        "end_equity": float(end_equity),
        "cagr": float(cagr),
        "max_drawdown": float(max_drawdown),
    }
