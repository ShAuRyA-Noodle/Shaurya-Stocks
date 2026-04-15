import pandas as pd
from fastapi import APIRouter, Depends
from backend.api.auth import require_api_key

router = APIRouter()


@router.get("/trades")
def get_trades(tier: str = Depends(require_api_key)):
    df = pd.read_csv("state/trades.csv")

    return {
        "trades": df.to_dict(orient="records"),
        "count": len(df),
    }
