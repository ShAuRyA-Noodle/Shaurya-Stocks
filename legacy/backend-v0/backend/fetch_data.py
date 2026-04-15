import yfinance as yf
import pandas as pd
from pathlib import Path
import argparse


DATA_DIR = Path("data/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = "2020-01-01"
END_DATE = None


def fetch_data(symbol: str):
    print(f"Fetching data for {symbol}...")
    df = yf.download(symbol, start=START_DATE, end=END_DATE)

    if df.empty:
        raise ValueError(f"No data fetched for {symbol}")

    df.reset_index(inplace=True)

    output_path = DATA_DIR / f"{symbol}_raw.csv"
    df.to_csv(output_path, index=False)

    print(f"Saved raw data to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, required=True)
    args = parser.parse_args()

    fetch_data(args.symbol.upper())
