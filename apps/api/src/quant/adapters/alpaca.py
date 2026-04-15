"""
Alpaca adapter — broker (paper + live), market data (IEX bars + quotes).

Splits the two concerns into `AlpacaBrokerAdapter` and `AlpacaDataAdapter`
so rate limits and base URLs stay distinct.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from quant.adapters.base import HttpAdapter
from quant.config import settings


# ================================================================
# Broker (orders + account + positions)
# ================================================================
class AlpacaBrokerAdapter(HttpAdapter):
    name = "alpaca_broker"
    calls_per_minute = 200

    def __init__(self, **kwargs: Any) -> None:
        self.base_url = settings.alpaca_base_url
        super().__init__(**kwargs)

    def default_headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": settings.alpaca_api_key_id.get_secret_value(),
            "APCA-API-SECRET-KEY": settings.alpaca_api_secret_key.get_secret_value(),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def account(self) -> dict[str, Any]:
        return await self.get_json("/v2/account")

    async def clock(self) -> dict[str, Any]:
        return await self.get_json("/v2/clock")

    async def positions(self) -> list[dict[str, Any]]:
        return await self.get_json("/v2/positions")

    async def orders(
        self, *, status: str = "open", limit: int = 100, nested: bool = True
    ) -> list[dict[str, Any]]:
        return await self.get_json(
            "/v2/orders",
            params={"status": status, "limit": limit, "nested": str(nested).lower()},
        )

    async def submit_order(
        self,
        *,
        symbol: str,
        qty: float,
        side: str,  # "buy" | "sell"
        type: str = "market",  # "market" | "limit"
        time_in_force: str = "day",
        limit_price: float | None = None,
        stop_price: float | None = None,
        client_order_id: str | None = None,
        extended_hours: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": type,
            "time_in_force": time_in_force,
            "extended_hours": extended_hours,
        }
        if limit_price is not None:
            body["limit_price"] = str(limit_price)
        if stop_price is not None:
            body["stop_price"] = str(stop_price)
        if client_order_id is not None:
            body["client_order_id"] = client_order_id
        return await self.post_json("/v2/orders", json=body)

    async def cancel_order(self, order_id: str) -> None:
        await self._request("DELETE", f"/v2/orders/{order_id}")

    async def cancel_all(self) -> list[dict[str, Any]]:
        resp = await self._request("DELETE", "/v2/orders")
        return resp.json() if resp.content else []


# ================================================================
# Market data (bars + quotes — IEX feed on free tier)
# ================================================================
class AlpacaDataAdapter(HttpAdapter):
    name = "alpaca_data"
    calls_per_minute = 200

    def __init__(self, **kwargs: Any) -> None:
        self.base_url = settings.alpaca_data_url
        super().__init__(**kwargs)

    def default_headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": settings.alpaca_api_key_id.get_secret_value(),
            "APCA-API-SECRET-KEY": settings.alpaca_api_secret_key.get_secret_value(),
            "Accept": "application/json",
        }

    async def bars(
        self,
        symbols: list[str],
        *,
        timeframe: str,  # "1Min" | "5Min" | "1Hour" | "1Day"
        start: datetime,
        end: datetime,
        adjustment: str = "split",
        feed: str = "iex",
        limit: int = 10_000,
    ) -> dict[str, list[dict[str, Any]]]:
        params: Mapping[str, Any] = {
            "symbols": ",".join(symbols),
            "timeframe": timeframe,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "adjustment": adjustment,
            "feed": feed,
            "limit": limit,
        }
        out: dict[str, list[dict[str, Any]]] = {}
        page_token: str | None = None
        while True:
            p = dict(params)
            if page_token:
                p["page_token"] = page_token
            data = await self.get_json("/v2/stocks/bars", params=p)
            for sym, rows in (data.get("bars") or {}).items():
                out.setdefault(sym, []).extend(rows)
            page_token = data.get("next_page_token")
            if not page_token:
                break
        return out

    async def latest_quotes(self, symbols: list[str], *, feed: str = "iex") -> dict[str, Any]:
        data = await self.get_json(
            "/v2/stocks/quotes/latest",
            params={"symbols": ",".join(symbols), "feed": feed},
        )
        return data.get("quotes") or {}
