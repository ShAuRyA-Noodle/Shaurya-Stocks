"""
Adapt the Kaggle S&P 500 5-year daily OHLCV snapshot to the runner schema.

Kaggle columns:  date, open, high, low, close, volume, Name
Runner columns: date, symbol, adj_close

We use `close` as `adj_close` — the Kaggle snapshot is already adjusted.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

SRC = Path(__file__).resolve().parents[4] / "data" / "legacy" / "all_stocks_5yr.csv"
DST = Path(__file__).parent / "sp500_5yr_adjusted.csv"


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"missing source file: {SRC}")

    df = (
        pl.read_csv(SRC, try_parse_dates=True)
        .select(
            pl.col("date").cast(pl.Date),
            pl.col("Name").alias("symbol"),
            pl.col("close").cast(pl.Float64).alias("adj_close"),
        )
        .drop_nulls()
        .sort(["symbol", "date"])
    )
    df.write_csv(DST)
    print(
        f"wrote {DST.relative_to(Path.cwd()) if DST.is_relative_to(Path.cwd()) else DST}\n"
        f"  rows:    {df.height:,}\n"
        f"  symbols: {df['symbol'].n_unique()}\n"
        f"  window:  {df['date'].min()} → {df['date'].max()}"
    )


if __name__ == "__main__":
    main()
