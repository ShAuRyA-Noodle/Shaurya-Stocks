"""
Marketaux — financial-tagged news feed with entity extraction + native sentiment.

Free: 100 requests/day.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quant.adapters.base import HttpAdapter
from quant.config import settings


class MarketauxAdapter(HttpAdapter):
    name = "marketaux"
    base_url = "https://api.marketaux.com"
    calls_per_minute = 10  # free tier is 100/day — go slow

    def default_headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}

    def _params_with_auth(self, params: Mapping[str, Any] | None) -> dict[str, Any]:
        merged: dict[str, Any] = dict(params or {})
        merged["api_token"] = settings.marketaux_api_key.get_secret_value()
        return merged

    async def news(
        self,
        *,
        symbols: list[str] | None = None,
        countries: str = "us",
        language: str = "en",
        limit: int = 3,  # free tier caps articles per call
        published_after: str | None = None,
        filter_entities: bool = True,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "countries": countries,
            "language": language,
            "limit": limit,
            "filter_entities": str(filter_entities).lower(),
        }
        if symbols:
            params["symbols"] = ",".join(symbols)
        if published_after:
            params["published_after"] = published_after
        data = await self.get_json("/v1/news/all", params=params)
        return data.get("data") or []
