"""
Prefect 3 flows for scheduled ingestion.

Deployments (Sprint 7 wires these to cron):
- bootstrap_flow:       one-shot; seeds universe + 10y OHLCV + macro backfill
- daily_close_flow:     18:00 ET weekday; yesterday's bars + corp actions + macro refresh
- hourly_news_flow:     :05 every hour; last-24h news across universe
- universe_refresh_flow: weekly Sunday; re-pulls SP500 + NDX100
"""

from __future__ import annotations

from datetime import date, timedelta

from prefect import flow, get_run_logger, task

from quant.ingest.corporate_actions import ingest_corporate_actions
from quant.ingest.macro import ingest_macro_series
from quant.ingest.news import ingest_news
from quant.ingest.ohlcv import backfill_ohlcv_daily
from quant.universe.loader import active_universe_symbols, bootstrap_universe


# ------------------------------------------------------------------
# Tasks — each wraps an async ingestion function
# ------------------------------------------------------------------
@task(retries=2, retry_delay_seconds=30)
async def _bootstrap_universe_task(enrich: bool) -> dict[str, int]:
    return await bootstrap_universe(enrich_with_polygon=enrich)


@task(retries=3, retry_delay_seconds=60, tags=["ingest", "ohlcv"])
async def _backfill_ohlcv_task(
    symbols: list[str], start: date, end: date
) -> dict[str, int]:
    return await backfill_ohlcv_daily(symbols, start=start, end=end)


@task(retries=2, retry_delay_seconds=30, tags=["ingest", "corp_actions"])
async def _ingest_corp_actions_task(symbols: list[str]) -> dict[str, int]:
    return await ingest_corporate_actions(symbols)


@task(retries=2, retry_delay_seconds=30, tags=["ingest", "macro"])
async def _ingest_macro_task(start: date | None) -> dict[str, int]:
    return await ingest_macro_series(start=start)


@task(retries=1, retry_delay_seconds=30, tags=["ingest", "news"])
async def _ingest_news_task(symbols: list[str], hours: int) -> dict[str, int]:
    return await ingest_news(symbols=symbols, lookback_hours=hours)


# ------------------------------------------------------------------
# Flows
# ------------------------------------------------------------------
@flow(name="bootstrap", log_prints=True)
async def bootstrap_flow(*, years: int = 10, enrich: bool = False) -> dict[str, int]:
    """One-shot: seed universe → 10y OHLCV → corp actions → 20y macro."""
    log = get_run_logger()
    res = await _bootstrap_universe_task(enrich=enrich)
    log.info("universe: %s", res)

    symbols = await active_universe_symbols("SP500")
    symbols = sorted(set(symbols + await active_universe_symbols("NDX100")))
    log.info("backfilling %d unique symbols", len(symbols))

    start = date.today() - timedelta(days=365 * years)
    end = date.today() - timedelta(days=1)

    ohlcv = await _backfill_ohlcv_task(symbols, start, end)
    corp = await _ingest_corp_actions_task(symbols)
    macro = await _ingest_macro_task(date.today() - timedelta(days=365 * 20))

    summary = {
        "universe_tickers": len(symbols),
        "ohlcv_symbols_ingested": sum(1 for v in ohlcv.values() if v > 0),
        "ohlcv_total_rows": sum(ohlcv.values()),
        "corp_action_rows": sum(corp.values()),
        "macro_series": len(macro),
    }
    log.info("bootstrap summary: %s", summary)
    return summary


@flow(name="daily_close", log_prints=True)
async def daily_close_flow() -> dict[str, int]:
    """Run after US close: yesterday's bars + corp actions + macro refresh."""
    log = get_run_logger()
    symbols = sorted(set(
        await active_universe_symbols("SP500")
        + await active_universe_symbols("NDX100")
    ))
    yday = date.today() - timedelta(days=1)
    ohlcv = await _backfill_ohlcv_task(symbols, yday, yday)
    corp = await _ingest_corp_actions_task(symbols)
    macro = await _ingest_macro_task(date.today() - timedelta(days=45))
    summary = {
        "ohlcv_rows": sum(ohlcv.values()),
        "corp_action_rows": sum(corp.values()),
        "macro_series": len(macro),
    }
    log.info("daily_close summary: %s", summary)
    return summary


@flow(name="hourly_news", log_prints=True)
async def hourly_news_flow() -> dict[str, int]:
    symbols = sorted(set(
        await active_universe_symbols("SP500")
        + await active_universe_symbols("NDX100")
    ))
    return await _ingest_news_task(symbols, 2)


@flow(name="universe_refresh", log_prints=True)
async def universe_refresh_flow() -> dict[str, int]:
    """Weekly: re-pull SP500 + NDX100 from public sources."""
    return await _bootstrap_universe_task(enrich=False)
