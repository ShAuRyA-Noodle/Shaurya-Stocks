"""
Finnhub — earnings calendar, insider transactions, recommendation trends,
company news. Free: 60 calls/min.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from quant.adapters.base import HttpAdapter
from quant.config import settings


class FinnhubAdapter(HttpAdapter):
    name = "finnhub"
    base_url = "https://finnhub.io/api/v1"
    calls_per_minute = 60

    def default_headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}

    def _params_with_auth(self, params: Mapping[str, Any] | None) -> dict[str, Any]:
        merged: dict[str, Any] = dict(params or {})
        merged["token"] = settings.finnhub_api_key.get_secret_value()
        return merged

    async def earnings_calendar(
        self, *, start: date, end: date, symbol: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"from": start.isoformat(), "to": end.isoformat()}
        if symbol:
            params["symbol"] = symbol
        data = await self.get_json("/calendar/earnings", params=params)
        return data.get("earningsCalendar") or []

    async def insider_transactions(
        self, symbol: str, *, start: date | None = None, end: date | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"symbol": symbol}
        if start:
            params["from"] = start.isoformat()
        if end:
            params["to"] = end.isoformat()
        data = await self.get_json("/stock/insider-transactions", params=params)
        return data.get("data") or []

    async def recommendation_trends(self, symbol: str) -> list[dict[str, Any]]:
        data = await self.get_json("/stock/recommendation", params={"symbol": symbol})
        return data if isinstance(data, list) else []

    async def company_news(self, symbol: str, *, start: date, end: date) -> list[dict[str, Any]]:
        data = await self.get_json(
            "/company-news",
            params={"symbol": symbol, "from": start.isoformat(), "to": end.isoformat()},
        )
        return data if isinstance(data, list) else []

    async def quote(self, symbol: str) -> dict[str, Any]:
        return await self.get_json("/quote", params={"symbol": symbol})
