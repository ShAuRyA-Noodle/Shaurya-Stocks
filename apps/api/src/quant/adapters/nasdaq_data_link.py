"""Nasdaq Data Link — free datasets (ex-Quandl). Rate limit: 20 calls/10s anon, 300/10s keyed."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from quant.adapters.base import HttpAdapter
from quant.adapters.exceptions import AuthenticationError
from quant.config import settings


class NasdaqDataLinkAdapter(HttpAdapter):
    name = "nasdaq_data_link"
    base_url = "https://data.nasdaq.com"
    calls_per_minute = 120

    def default_headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}

    def _params_with_auth(self, params: Mapping[str, Any] | None) -> dict[str, Any]:
        merged: dict[str, Any] = dict(params or {})
        if settings.nasdaq_data_link_api_key is not None:
            merged["api_key"] = settings.nasdaq_data_link_api_key.get_secret_value()
        return merged

    async def dataset(
        self,
        *,
        database_code: str,
        dataset_code: str,
        start: date | None = None,
        end: date | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        if settings.nasdaq_data_link_api_key is None:
            raise AuthenticationError(self.name, 401, "NASDAQ_DATA_LINK_API_KEY not configured")
        params: dict[str, Any] = {}
        if start:
            params["start_date"] = start.isoformat()
        if end:
            params["end_date"] = end.isoformat()
        if limit:
            params["limit"] = limit
        data = await self.get_json(
            f"/api/v3/datasets/{database_code}/{dataset_code}/data.json", params=params
        )
        return data.get("dataset_data") or {}
