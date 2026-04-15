"""NewsAPI — general news fallback. Free: 100 req/day, 24h delay on articles."""

from __future__ import annotations

from typing import Any

from quant.adapters.base import HttpAdapter
from quant.adapters.exceptions import AuthenticationError
from quant.config import settings


class NewsApiAdapter(HttpAdapter):
    name = "newsapi"
    base_url = "https://newsapi.org"
    calls_per_minute = 5  # free daily cap => stay slow

    def default_headers(self) -> dict[str, str]:
        if settings.newsapi_key is None:
            return {"Accept": "application/json"}
        return {
            "X-Api-Key": settings.newsapi_key.get_secret_value(),
            "Accept": "application/json",
        }

    def _require_key(self) -> None:
        if settings.newsapi_key is None:
            raise AuthenticationError(self.name, 401, "NEWSAPI_KEY not configured")

    async def everything(
        self,
        *,
        query: str,
        from_iso: str | None = None,
        to_iso: str | None = None,
        language: str = "en",
        sort_by: str = "publishedAt",
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        self._require_key()
        params: dict[str, Any] = {
            "q": query, "language": language, "sortBy": sort_by, "pageSize": page_size,
        }
        if from_iso:
            params["from"] = from_iso
        if to_iso:
            params["to"] = to_iso
        data = await self.get_json("/v2/everything", params=params)
        return data.get("articles") or []

    async def top_headlines(
        self, *, category: str = "business", country: str = "us", page_size: int = 50
    ) -> list[dict[str, Any]]:
        self._require_key()
        data = await self.get_json(
            "/v2/top-headlines",
            params={"category": category, "country": country, "pageSize": page_size},
        )
        return data.get("articles") or []
