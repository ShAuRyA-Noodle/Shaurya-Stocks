"""
Tiingo — OHLCV fallback (adjusted daily), fundamentals, IEX intraday quotes.

Free tier: 500 unique symbols / 1000 req-hr / 50 req-hr-per-endpoint.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from quant.adapters.base import HttpAdapter
from quant.config import settings


class TiingoAdapter(HttpAdapter):
    name = "tiingo"
    base_url = "https://api.tiingo.com"
    calls_per_minute = 60  # conservative

    def default_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Token {settings.tiingo_api_key.get_secret_value()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def metadata(self, symbol: str) -> dict[str, Any]:
        return await self.get_json(f"/tiingo/daily/{symbol}")

    async def daily_prices(
        self,
        symbol: str,
        *,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """
        Returns adjusted daily bars. Tiingo shape:
        { date, close, high, low, open, volume, adjClose, adjHigh, adjLow, adjOpen, adjVolume, divCash, splitFactor }
        """
        data = await self.get_json(
            f"/tiingo/daily/{symbol}/prices",
            params={"startDate": start.isoformat(), "endDate": end.isoformat()},
        )
        return data if isinstance(data, list) else []

    async def iex_last(self, symbols: list[str]) -> list[dict[str, Any]]:
        data = await self.get_json("/iex", params={"tickers": ",".join(symbols)})
        return data if isinstance(data, list) else []

    async def fundamentals_statements(self, symbol: str) -> list[dict[str, Any]]:
        data = await self.get_json(f"/tiingo/fundamentals/{symbol}/statements")
        return data if isinstance(data, list) else []

    async def news(
        self, *, tickers: list[str] | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "sortBy": "publishedDate"}
        if tickers:
            params["tickers"] = ",".join(tickers)
        data = await self.get_json("/tiingo/news", params=params)
        return data if isinstance(data, list) else []
