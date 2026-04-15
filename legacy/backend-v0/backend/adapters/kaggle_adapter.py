import pandas as pd
from pathlib import Path

INPUT = Path("data/external/kaggle_msft.csv")
OUTPUT = Path("data/raw/MSFT_raw.csv")

df = pd.read_csv(INPUT)

df = df.rename(columns={
    "date": "Date",
    "open": "Open",
    "high": "High",
    "low": "Low",
    "close": "Close",
    "volume": "Volume"
})

df.to_csv(OUTPUT, index=False)
print("Kaggle data adapted successfully")
