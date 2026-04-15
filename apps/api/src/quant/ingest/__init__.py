"""Ingestion layer — adapters → canonical DB rows."""

from quant.ingest.corporate_actions import ingest_corporate_actions
from quant.ingest.macro import ingest_macro_series
from quant.ingest.news import ingest_news
from quant.ingest.ohlcv import backfill_ohlcv_daily

__all__ = [
    "backfill_ohlcv_daily",
    "ingest_corporate_actions",
    "ingest_macro_series",
    "ingest_news",
]
