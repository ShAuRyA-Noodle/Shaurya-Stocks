"""
Polygon.io adapter — primary OHLCV, ticker metadata, corporate actions, news.

Free plan limits: ~5 calls/min. Starter plan: unlimited but 5-year history.
Configured budget: 5/min (safe default) — raise via settings if on paid plan.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from datetime import date
from typing import Any

from quant.adapters.base import HttpAdapter
from quant.config import settings


class PolygonAdapter(HttpAdapter):
    name = "polygon"
    base_url = "https://api.polygon.io"
    calls_per_minute = 5  # free-tier safe

    def default_headers(self) -> dict[str, str]:
        return {"Accept": "application/json", "User-Agent": "quant-platform/1.0"}

    def _params_with_auth(self, params: Mapping[str, Any] | None) -> dict[str, Any]:
        merged: dict[str, Any] = dict(params or {})
        merged["apiKey"] = settings.polygon_api_key.get_secret_value()
        return merged

    # ------------------------------------------------------------
    # Tickers
    # ------------------------------------------------------------
    async def list_tickers(
        self,
        *,
        market: str = "stocks",
        active: bool = True,
        limit: int = 1000,
    ) -> AsyncIterator[dict[str, Any]]:
        """Paginated iterator over Polygon's reference tickers."""
        url = "/v3/reference/tickers"
        params: dict[str, Any] = {"market": market, "active": str(active).lower(), "limit": limit}
        while True:
            data = await self.get_json(url, params=params)
            for row in data.get("results", []):
                yield row
            next_url = data.get("next_url")
            if not next_url:
                return
            # Polygon returns absolute URL; strip base and reuse
            url = next_url.replace(self.base_url, "")
            params = {}  # next_url already carries the cursor

    async def ticker_details(self, symbol: str) -> dict[str, Any]:
        data = await self.get_json(f"/v3/reference/tickers/{symbol}")
        return data.get("results") or {}

    # ------------------------------------------------------------
    # OHLCV — aggregates (bars)
    # ------------------------------------------------------------
    async def aggregates(
        self,
        symbol: str,
        *,
        start: date,
        end: date,
        multiplier: int = 1,
        timespan: str = "day",
        adjusted: bool = True,
        limit: int = 50_000,
    ) -> list[dict[str, Any]]:
        """
        Returns bars between start and end (inclusive), oldest first.
        Polygon key shape: { t: ms epoch, o, h, l, c, v, vw, n }
        """
        path = f"/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start.isoformat()}/{end.isoformat()}"
        params = {"adjusted": str(adjusted).lower(), "sort": "asc", "limit": limit}
        data = await self.get_json(path, params=params)
        return data.get("results") or []

    async def daily_bars(
        self, symbol: str, start: date, end: date, *, adjusted: bool = True
    ) -> list[dict[str, Any]]:
        return await self.aggregates(
            symbol, start=start, end=end, multiplier=1, timespan="day", adjusted=adjusted
        )

    # ------------------------------------------------------------
    # Corporate actions
    # ------------------------------------------------------------
    async def splits(self, symbol: str) -> list[dict[str, Any]]:
        data = await self.get_json("/v3/reference/splits", params={"ticker": symbol, "limit": 1000})
        return data.get("results") or []

    async def dividends(self, symbol: str) -> list[dict[str, Any]]:
        data = await self.get_json("/v3/reference/dividends", params={"ticker": symbol, "limit": 1000})
        return data.get("results") or []

    # ------------------------------------------------------------
    # News
    # ------------------------------------------------------------
    async def news(
        self, *, ticker: str | None = None, limit: int = 50, published_gte: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "order": "desc", "sort": "published_utc"}
        if ticker:
            params["ticker"] = ticker
        if published_gte:
            params["published_utc.gte"] = published_gte
        data = await self.get_json("/v2/reference/news", params=params)
        return data.get("results") or []

    # ------------------------------------------------------------
    # Market status (for scheduling)
    # ------------------------------------------------------------
    async def market_status(self) -> dict[str, Any]:
        return await self.get_json("/v1/marketstatus/now")
