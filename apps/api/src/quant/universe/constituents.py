"""
Source of truth for the SP500 and NDX100 constituent lists.

Both pull from public, stable, authoritative sources at bootstrap time:
- SP500: DataHub CC0 CSV (derived from S&P Dow Jones + Wikipedia)
- NDX100: Wikipedia table (scraped with pandas.read_html via httpx)

Historical point-in-time membership (for survivorship-bias elimination in
backtests) requires a paid vendor feed — the DB schema supports it, and
`market.universe_membership` rows can be amended later without code changes.

For offline dev / CI / quick starts, `DEV_UNIVERSE` is a 20-name highly-liquid
subset that spans sectors.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Literal

import httpx

UniverseName = Literal["SP500", "NDX100", "DEV"]

# ------------------------------------------------------------------
# DEV universe — 20 highly liquid names, sector-diversified
# ------------------------------------------------------------------
DEV_UNIVERSE: tuple[str, ...] = (
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO",
    "JPM", "V", "MA", "WMT", "UNH", "JNJ", "PG", "XOM",
    "HD", "LLY", "COST", "KO",
)

# ------------------------------------------------------------------
# Stable public sources
# ------------------------------------------------------------------
SP500_CSV_URL = (
    "https://raw.githubusercontent.com/datasets/"
    "s-and-p-500-companies/main/data/constituents.csv"
)
NDX100_WIKI_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"

_HEADERS = {"User-Agent": "quant-platform/1.0 (bootstrap-universe)"}

# ------------------------------------------------------------------
# SP500 — DataHub CSV
# ------------------------------------------------------------------
async def fetch_sp500(client: httpx.AsyncClient | None = None) -> list[dict[str, str]]:
    """
    Returns a list of {symbol, name, sector} dicts.
    Symbols are normalized: "BRK.B" → "BRK.B" (kept as-is for Polygon;
    Alpaca uses "BRK.B" as well).
    """
    owns = client is None
    client = client or httpx.AsyncClient(timeout=30.0, headers=_HEADERS)
    try:
        resp = await client.get(SP500_CSV_URL)
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        out: list[dict[str, str]] = []
        for row in reader:
            sym = (row.get("Symbol") or "").strip()
            if not sym:
                continue
            out.append({
                "symbol": sym,
                "name": (row.get("Security") or "").strip(),
                "sector": (row.get("GICS Sector") or "").strip(),
                "industry": (row.get("GICS Sub-Industry") or "").strip(),
            })
        return out
    finally:
        if owns:
            await client.aclose()


# ------------------------------------------------------------------
# NDX100 — Wikipedia scrape (light regex over the HTML tables)
# ------------------------------------------------------------------
# The Nasdaq-100 page has a wikitable whose rows start with a <td> containing
# <a> tags for company name + ticker. We grep each wikitable row and pull the
# ticker out of the cell that looks like a ticker (ALL-CAPS 1-5 chars).
_WIKI_TICKER_ROW = re.compile(
    r"<tr>.*?<td[^>]*>.*?</td>.*?<td[^>]*>\s*<a[^>]*>([A-Z][A-Z0-9.\-]{0,9})</a>",
    re.DOTALL,
)


async def fetch_ndx100(client: httpx.AsyncClient | None = None) -> list[dict[str, str]]:
    """
    Returns a list of {symbol, name, sector} dicts for the Nasdaq-100.

    Wikipedia's structure is stable enough that we can regex the ticker column
    of the "Components" wikitable. Defensive: any row that doesn't match the
    expected pattern is silently skipped — the caller should assert len >= 95.
    """
    owns = client is None
    client = client or httpx.AsyncClient(timeout=30.0, headers=_HEADERS)
    try:
        resp = await client.get(NDX100_WIKI_URL)
        resp.raise_for_status()
        html = resp.text

        # Isolate the Components table — it's the first wikitable with "Ticker" in it
        m = re.search(
            r'<table class="wikitable[^"]*"[^>]*id="constituents".*?</table>',
            html, re.DOTALL,
        )
        if not m:
            # Fallback: first wikitable with a "Ticker" header
            m = re.search(
                r'<table class="wikitable[^"]*"[^>]*>\s*<caption[^>]*>.*?</caption>.*?</table>',
                html, re.DOTALL,
            )
        table_html = m.group(0) if m else html

        tickers: list[dict[str, str]] = []
        seen: set[str] = set()
        for row in re.finditer(r"<tr>.*?</tr>", table_html, re.DOTALL):
            cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row.group(0), re.DOTALL)
            if len(cells) < 2:
                continue
            # Strip HTML tags
            stripped = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
            # The ticker cell is the one that's ALL-CAPS 1-5 chars (with optional . or -)
            ticker = None
            for val in stripped:
                if re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,5}", val):
                    ticker = val
                    break
            if not ticker or ticker in seen:
                continue
            seen.add(ticker)
            name = stripped[0] if stripped[0] != ticker else (stripped[1] if len(stripped) > 1 else "")
            tickers.append({"symbol": ticker, "name": name, "sector": "", "industry": ""})

        return tickers
    finally:
        if owns:
            await client.aclose()
