"""Alpha Vantage — last-resort OHLCV fallback + FX. Free: 25 req/day, 5 req/min."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quant.adapters.base import HttpAdapter
from quant.adapters.exceptions import AuthenticationError
from quant.config import settings


class AlphaVantageAdapter(HttpAdapter):
    name = "alphavantage"
    base_url = "https://www.alphavantage.co"
    calls_per_minute = 5  # hard cap on free tier

    def default_headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}

    def _params_with_auth(self, params: Mapping[str, Any] | None) -> dict[str, Any]:
        if settings.alphavantage_api_key is None:
            raise AuthenticationError(self.name, 401, "ALPHAVANTAGE_API_KEY not configured")
        merged: dict[str, Any] = dict(params or {})
        merged["apikey"] = settings.alphavantage_api_key.get_secret_value()
        return merged

    async def daily_adjusted(self, symbol: str, *, full: bool = True) -> dict[str, Any]:
        data = await self.get_json(
            "/query",
            params={
                "function": "TIME_SERIES_DAILY_ADJUSTED",
                "symbol": symbol,
                "outputsize": "full" if full else "compact",
                "datatype": "json",
            },
        )
        return data.get("Time Series (Daily)") or {}

    async def fx_daily(self, from_sym: str, to_sym: str, *, full: bool = False) -> dict[str, Any]:
        data = await self.get_json(
            "/query",
            params={
                "function": "FX_DAILY",
                "from_symbol": from_sym,
                "to_symbol": to_sym,
                "outputsize": "full" if full else "compact",
            },
        )
        return data.get("Time Series FX (Daily)") or {}
