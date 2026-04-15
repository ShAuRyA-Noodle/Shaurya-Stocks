"""
Quant platform CLI.

    quant universe bootstrap [--enrich]
    quant backfill ohlcv  --start 2016-01-01 [--end YYYY-MM-DD] [--universe SP500|NDX100|SP500_NDX100|DEV]
    quant backfill macro  [--start YYYY-MM-DD]
    quant backfill news   [--hours 24]
    quant flow bootstrap  [--years 10]

Run via `python -m quant.cli ...` or the entrypoint `quant ...`.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, timedelta
from typing import Annotated

import typer

from quant.config import settings
from quant.universe.constituents import DEV_UNIVERSE

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)
universe_app = typer.Typer(help="Universe operations.")
backfill_app = typer.Typer(help="Data backfills.")
flow_app = typer.Typer(help="Run Prefect flows locally (no orchestrator).")
app.add_typer(universe_app, name="universe")
app.add_typer(backfill_app, name="backfill")
app.add_typer(flow_app, name="flow")


def _setup_logging() -> None:
    logging.basicConfig(
        level=settings.app_log_level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )


def _run(coro):  # type: ignore[no-untyped-def]
    _setup_logging()
    return asyncio.run(coro)


# ---------------------------------------------------------------
# universe
# ---------------------------------------------------------------
@universe_app.command("bootstrap")
def universe_bootstrap(
    enrich: Annotated[bool, typer.Option(help="Also enrich metadata via Polygon")] = False,
) -> None:
    """Seed SP500 + NDX100 tickers + membership."""
    from quant.universe import bootstrap_universe

    res = _run(bootstrap_universe(enrich_with_polygon=enrich))
    typer.echo(json.dumps(res, indent=2))


@universe_app.command("list")
def universe_list(
    universe: Annotated[str, typer.Option(help="SP500 | NDX100 | DEV")] = "SP500",
) -> None:
    from quant.universe.loader import active_universe_symbols

    if universe == "DEV":
        typer.echo("\n".join(DEV_UNIVERSE))
        return
    syms = _run(active_universe_symbols(universe))
    typer.echo(f"# {universe}: {len(syms)} symbols")
    typer.echo("\n".join(syms))


# ---------------------------------------------------------------
# backfill
# ---------------------------------------------------------------
def _resolve_symbols(universe: str) -> list[str]:
    from quant.universe.loader import active_universe_symbols

    if universe == "DEV":
        return list(DEV_UNIVERSE)
    if universe == "SP500_NDX100":
        a = _run(active_universe_symbols("SP500"))
        b = _run(active_universe_symbols("NDX100"))
        return sorted(set(a + b))
    return _run(active_universe_symbols(universe))


@backfill_app.command("ohlcv")
def backfill_ohlcv(
    start: Annotated[str, typer.Option(help="YYYY-MM-DD inclusive")] = "",
    end: Annotated[str, typer.Option(help="YYYY-MM-DD inclusive; default = yesterday")] = "",
    universe: Annotated[str, typer.Option(help="SP500 | NDX100 | SP500_NDX100 | DEV")] = "SP500_NDX100",
    years: Annotated[int, typer.Option(help="Convenience: years back from today if --start omitted")] = 10,
) -> None:
    from quant.ingest.ohlcv import backfill_ohlcv_daily

    start_d = date.fromisoformat(start) if start else (date.today() - timedelta(days=365 * years))
    end_d = date.fromisoformat(end) if end else (date.today() - timedelta(days=1))
    symbols = _resolve_symbols(universe)
    typer.echo(f"OHLCV backfill: {len(symbols)} symbols, {start_d} → {end_d}")
    res = _run(backfill_ohlcv_daily(symbols, start=start_d, end=end_d))
    ok = sum(1 for v in res.values() if v > 0)
    total = sum(res.values())
    typer.echo(f"Done: {ok}/{len(symbols)} symbols, {total} rows")


@backfill_app.command("corp-actions")
def backfill_corp_actions(
    universe: Annotated[str, typer.Option()] = "SP500_NDX100",
) -> None:
    from quant.ingest.corporate_actions import ingest_corporate_actions

    symbols = _resolve_symbols(universe)
    res = _run(ingest_corporate_actions(symbols))
    typer.echo(f"{sum(res.values())} corp-action rows across {len(symbols)} symbols")


@backfill_app.command("macro")
def backfill_macro(
    start: Annotated[str, typer.Option()] = "",
) -> None:
    from quant.ingest.macro import ingest_macro_series

    start_d = date.fromisoformat(start) if start else None
    res = _run(ingest_macro_series(start=start_d))
    typer.echo(json.dumps(res, indent=2))


@backfill_app.command("news")
def backfill_news(
    hours: Annotated[int, typer.Option()] = 24,
    universe: Annotated[str, typer.Option()] = "SP500_NDX100",
) -> None:
    from quant.ingest.news import ingest_news

    symbols = _resolve_symbols(universe)
    res = _run(ingest_news(symbols=symbols, lookback_hours=hours))
    typer.echo(json.dumps(res, indent=2))


# ---------------------------------------------------------------
# flow (local, no Prefect server required)
# ---------------------------------------------------------------
@flow_app.command("bootstrap")
def flow_bootstrap(
    years: Annotated[int, typer.Option()] = 10,
    enrich: Annotated[bool, typer.Option()] = False,
) -> None:
    from quant.workers.flows import bootstrap_flow

    res = _run(bootstrap_flow(years=years, enrich=enrich))
    typer.echo(json.dumps(res, indent=2))


@flow_app.command("daily-close")
def flow_daily_close() -> None:
    from quant.workers.flows import daily_close_flow

    res = _run(daily_close_flow())
    typer.echo(json.dumps(res, indent=2))


@flow_app.command("hourly-news")
def flow_hourly_news() -> None:
    from quant.workers.flows import hourly_news_flow

    res = _run(hourly_news_flow())
    typer.echo(json.dumps(res, indent=2))


if __name__ == "__main__":
    app()
