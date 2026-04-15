import pandas as pd
from fastapi import APIRouter, Depends
from backend.api.auth import require_api_key

router = APIRouter()


@router.get("/signals")
def get_signals(tier: str = Depends(require_api_key)):
    df = pd.read_csv("state/daily_signals.csv")

    return {
        "signals": df.to_dict(orient="records"),
        "count": len(df),
    }
