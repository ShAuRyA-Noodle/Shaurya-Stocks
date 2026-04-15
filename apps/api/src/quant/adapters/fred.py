"""
FRED — macro series (VIX, DGS10, DXY, CPI, UNRATE, …).

Free tier: 120 requests/min. Plenty of room.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from quant.adapters.base import HttpAdapter
from quant.config import settings


class FredAdapter(HttpAdapter):
    name = "fred"
    base_url = "https://api.stlouisfed.org"
    calls_per_minute = 120

    def default_headers(self) -> dict[str, str]:
        return {"Accept": "application/json", "User-Agent": "quant-platform/1.0"}

    def _params_with_auth(self, params: Mapping[str, Any] | None) -> dict[str, Any]:
        merged: dict[str, Any] = dict(params or {})
        merged["api_key"] = settings.fred_api_key.get_secret_value()
        merged.setdefault("file_type", "json")
        return merged

    async def series_info(self, series_id: str) -> dict[str, Any]:
        data = await self.get_json("/fred/series", params={"series_id": series_id})
        rows = data.get("seriess") or []
        return rows[0] if rows else {}

    async def observations(
        self,
        series_id: str,
        *,
        start: date | None = None,
        end: date | None = None,
        limit: int = 100_000,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "series_id": series_id,
            "limit": limit,
            "sort_order": "asc",
        }
        if start:
            params["observation_start"] = start.isoformat()
        if end:
            params["observation_end"] = end.isoformat()
        data = await self.get_json("/fred/series/observations", params=params)
        return data.get("observations") or []


# Canonical series we care about (regime model + feature engineering)
MACRO_SERIES: dict[str, str] = {
    "VIXCLS": "CBOE Volatility Index",
    "DGS10": "10-Year Treasury Constant Maturity",
    "DGS2": "2-Year Treasury Constant Maturity",
    "DGS3MO": "3-Month Treasury Bill",
    "DTWEXBGS": "DXY (trade-weighted dollar, broad)",
    "T10Y2Y": "10Y-2Y Treasury Spread",
    "T10YIE": "10-year Breakeven Inflation",
    "UNRATE": "Unemployment Rate",
    "CPIAUCSL": "CPI All Urban",
    "FEDFUNDS": "Federal Funds Rate",
    "HYIELDSPREAD": "High-Yield OAS",  # BAMLH0A0HYM2 in practice — aliased at ingest time
    "BAMLH0A0HYM2": "ICE BofA US High Yield OAS",
}
