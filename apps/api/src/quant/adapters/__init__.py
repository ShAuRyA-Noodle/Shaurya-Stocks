"""Provider adapters — one class per upstream, uniform async HTTP surface."""

from quant.adapters.alphavantage import AlphaVantageAdapter
from quant.adapters.alpaca import AlpacaBrokerAdapter, AlpacaDataAdapter
from quant.adapters.base import HttpAdapter, TokenBucket
from quant.adapters.exceptions import (
    AdapterError,
    AuthenticationError,
    DataQualityError,
    ProviderError,
    RateLimitError,
    TransientError,
)
from quant.adapters.finnhub import FinnhubAdapter
from quant.adapters.fmp import FmpAdapter
from quant.adapters.fred import MACRO_SERIES, FredAdapter
from quant.adapters.groq import GroqAdapter
from quant.adapters.marketaux import MarketauxAdapter
from quant.adapters.nasdaq_data_link import NasdaqDataLinkAdapter
from quant.adapters.newsapi import NewsApiAdapter
from quant.adapters.polygon import PolygonAdapter
from quant.adapters.tiingo import TiingoAdapter

__all__ = [
    "HttpAdapter",
    "TokenBucket",
    "AdapterError",
    "AuthenticationError",
    "DataQualityError",
    "ProviderError",
    "RateLimitError",
    "TransientError",
    "PolygonAdapter",
    "AlpacaBrokerAdapter",
    "AlpacaDataAdapter",
    "FredAdapter",
    "MACRO_SERIES",
    "TiingoAdapter",
    "FinnhubAdapter",
    "MarketauxAdapter",
    "NewsApiAdapter",
    "FmpAdapter",
    "NasdaqDataLinkAdapter",
    "AlphaVantageAdapter",
    "GroqAdapter",
]
