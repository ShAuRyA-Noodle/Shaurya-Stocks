"""Per-adapter smoke tests via httpx MockTransport."""

from __future__ import annotations

from datetime import date, datetime

import httpx
import pytest

from quant.adapters.alpaca import AlpacaBrokerAdapter, AlpacaDataAdapter
from quant.adapters.finnhub import FinnhubAdapter
from quant.adapters.fred import FredAdapter
from quant.adapters.groq import GroqAdapter
from quant.adapters.marketaux import MarketauxAdapter
from quant.adapters.polygon import PolygonAdapter
from quant.adapters.tiingo import TiingoAdapter


# -------------------------------------------------------------------
# Polygon — aggregates path + apiKey injection
# -------------------------------------------------------------------
async def test_polygon_daily_bars_roundtrip() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "results": [
                    {
                        "t": 1714089600000,
                        "o": 100.0,
                        "h": 110.0,
                        "l": 95.0,
                        "c": 108.0,
                        "v": 1_000_000,
                        "vw": 104.5,
                        "n": 12345,
                    },
                ],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.polygon.io")
    p = PolygonAdapter(client=client)
    bars = await p.daily_bars("AAPL", date(2024, 1, 1), date(2024, 1, 31))
    await p.aclose()

    assert len(bars) == 1
    assert bars[0]["c"] == 108.0
    assert "/v2/aggs/ticker/AAPL/range/1/day/2024-01-01/2024-01-31" in seen["url"]
    assert "apiKey" in seen["params"]


# -------------------------------------------------------------------
# Alpaca — broker headers
# -------------------------------------------------------------------
async def test_alpaca_broker_sends_auth_headers() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.headers))
        return httpx.Response(200, json={"cash": "100000"})

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://paper-api.alpaca.markets"
    )
    a = AlpacaBrokerAdapter(client=client)
    data = await a.account()
    await a.aclose()

    assert data == {"cash": "100000"}
    assert "apca-api-key-id" in {k.lower() for k in captured}
    assert "apca-api-secret-key" in {k.lower() for k in captured}


async def test_alpaca_data_bars_pagination() -> None:
    state = {"page": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["page"] += 1
        if state["page"] == 1:
            return httpx.Response(
                200,
                json={
                    "bars": {
                        "AAPL": [{"t": "2024-01-02T14:30:00Z", "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 100}]
                    },
                    "next_page_token": "abc",
                },
            )
        return httpx.Response(
            200,
            json={
                "bars": {
                    "AAPL": [{"t": "2024-01-03T14:30:00Z", "o": 1.5, "h": 2, "l": 1, "c": 1.9, "v": 200}]
                },
                "next_page_token": None,
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://data.alpaca.markets")
    a = AlpacaDataAdapter(client=client)
    bars = await a.bars(
        ["AAPL"],
        timeframe="1Day",
        start=datetime(2024, 1, 2),
        end=datetime(2024, 1, 3),
    )
    await a.aclose()

    assert len(bars["AAPL"]) == 2


# -------------------------------------------------------------------
# FRED
# -------------------------------------------------------------------
async def test_fred_observations_filetype_injected() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return httpx.Response(200, json={"observations": [{"date": "2024-01-01", "value": "20.5"}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.stlouisfed.org")
    f = FredAdapter(client=client)
    obs = await f.observations("VIXCLS")
    await f.aclose()

    assert obs == [{"date": "2024-01-01", "value": "20.5"}]
    assert seen["file_type"] == "json"
    assert "api_key" in seen


# -------------------------------------------------------------------
# Tiingo — auth header
# -------------------------------------------------------------------
async def test_tiingo_sends_token_header() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update({k.lower(): v for k, v in request.headers.items()})
        return httpx.Response(
            200,
            json=[
                {
                    "date": "2024-01-02",
                    "open": 1,
                    "high": 2,
                    "low": 1,
                    "close": 1.5,
                    "adjClose": 1.5,
                    "volume": 100,
                }
            ],
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.tiingo.com")
    t = TiingoAdapter(client=client)
    rows = await t.daily_prices("AAPL", start=date(2024, 1, 1), end=date(2024, 1, 5))
    await t.aclose()

    assert rows[0]["adjClose"] == 1.5
    assert captured["authorization"].startswith("Token ")


# -------------------------------------------------------------------
# Finnhub — token in query
# -------------------------------------------------------------------
async def test_finnhub_token_in_query() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return httpx.Response(200, json={"earningsCalendar": [{"symbol": "AAPL"}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://finnhub.io/api/v1")
    f = FinnhubAdapter(client=client)
    await f.earnings_calendar(start=date(2024, 1, 1), end=date(2024, 1, 31))
    await f.aclose()

    assert "token" in seen


# -------------------------------------------------------------------
# Marketaux
# -------------------------------------------------------------------
async def test_marketaux_news_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "uuid": "a",
                        "url": "https://x",
                        "title": "t",
                        "published_at": "2024-01-02T12:00:00Z",
                        "entities": [{"symbol": "AAPL"}],
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.marketaux.com")
    m = MarketauxAdapter(client=client)
    data = await m.news(symbols=["AAPL"])
    await m.aclose()

    assert data[0]["uuid"] == "a"


# -------------------------------------------------------------------
# Groq — sentiment JSON parsing
# -------------------------------------------------------------------
async def test_groq_sentiment_parses_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"score": 0.7, "label": "bullish", "rationale": "strong beat"}'}}
                ]
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://api.groq.com/openai/v1"
    )
    g = GroqAdapter(client=client)
    out = await g.score_sentiment(headline="Apple beats earnings", summary=None, tickers=["AAPL"])
    await g.aclose()

    assert out["score"] == pytest.approx(0.7)
    assert out["label"] == "bullish"


async def test_groq_sentiment_clamps_score() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"score": 2.5, "label": "ufo"}'}}]},
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://api.groq.com/openai/v1"
    )
    g = GroqAdapter(client=client)
    out = await g.score_sentiment(headline="x", summary=None, tickers=[])
    await g.aclose()

    assert out["score"] == 1.0  # clamped
    assert out["label"] == "neutral"  # invalid label replaced
