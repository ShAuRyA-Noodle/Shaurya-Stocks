"""
Financial Modeling Prep — analyst price targets, estimates, upgrades/downgrades,
fundamentals. Free: 250 calls/day.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quant.adapters.base import HttpAdapter
from quant.adapters.exceptions import AuthenticationError
from quant.config import settings


class FmpAdapter(HttpAdapter):
    name = "fmp"
    base_url = "https://financialmodelingprep.com"
    calls_per_minute = 10

    def default_headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}

    def _params_with_auth(self, params: Mapping[str, Any] | None) -> dict[str, Any]:
        if settings.fmp_api_key is None:
            raise AuthenticationError(self.name, 401, "FMP_API_KEY not configured")
        merged: dict[str, Any] = dict(params or {})
        merged["apikey"] = settings.fmp_api_key.get_secret_value()
        return merged

    async def price_target_consensus(self, symbol: str) -> list[dict[str, Any]]:
        data = await self.get_json(
            "/api/v4/price-target-consensus", params={"symbol": symbol}
        )
        return data if isinstance(data, list) else []

    async def analyst_estimates(self, symbol: str) -> list[dict[str, Any]]:
        data = await self.get_json(f"/api/v3/analyst-estimates/{symbol}")
        return data if isinstance(data, list) else []

    async def upgrades_downgrades(self, symbol: str) -> list[dict[str, Any]]:
        data = await self.get_json("/api/v4/upgrades-downgrades", params={"symbol": symbol})
        return data if isinstance(data, list) else []

    async def key_metrics(self, symbol: str, *, period: str = "annual") -> list[dict[str, Any]]:
        data = await self.get_json(
            f"/api/v3/key-metrics/{symbol}", params={"period": period, "limit": 40}
        )
        return data if isinstance(data, list) else []
