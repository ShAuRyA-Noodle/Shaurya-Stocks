"""Tests for point-in-time S&P 500 membership reconstruction."""

from __future__ import annotations

from datetime import date

import pytest

from quant.universe.point_in_time import (
    IndexChange,
    _parse_date,
    members_as_of,
    parse_changes_html,
)


# ------------------------------------------------------------------
# Date parsing
# ------------------------------------------------------------------
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("January 26, 2024", date(2024, 1, 26)),
        ("October 2, 2023", date(2023, 10, 2)),
        ("2024-01-26", date(2024, 1, 26)),
        ("garbage", None),
        ("", None),
    ],
)
def test_parse_date(text: str, expected: date | None) -> None:
    assert _parse_date(text) == expected


# ------------------------------------------------------------------
# HTML parsing — fixture mirrors real Wikipedia wikitable structure
# ------------------------------------------------------------------
_FIXTURE_HTML = """
<html><body>
<table class="wikitable sortable">
  <tr><th>Symbol</th><th>Security</th></tr>
  <tr><td>AAPL</td><td>Apple Inc.</td></tr>
</table>

<h2>Selected changes to the list of S&P 500 components</h2>
<table class="wikitable sortable">
  <tr>
    <th>Date</th>
    <th colspan="2">Added</th>
    <th colspan="2">Removed</th>
    <th>Reason</th>
  </tr>
  <tr>
    <th></th>
    <th>Ticker</th><th>Security</th>
    <th>Ticker</th><th>Security</th>
    <th></th>
  </tr>
  <tr>
    <td>March 15, 2024</td>
    <td>SMCI</td><td>Super Micro Computer</td>
    <td>WHR</td><td>Whirlpool</td>
    <td>Market cap rebalancing[1]</td>
  </tr>
  <tr>
    <td>October 2, 2023</td>
    <td>BLDR</td><td>Builders FirstSource</td>
    <td>DXC</td><td>DXC Technology</td>
    <td>Acquisition</td>
  </tr>
  <tr>
    <td>2020-12-21</td>
    <td>TSLA</td><td>Tesla, Inc.</td>
    <td>AIV</td><td>Apartment Investment</td>
    <td>Spin-off</td>
  </tr>
</table>
</body></html>
"""


def test_parse_changes_html_extracts_three_events() -> None:
    changes = parse_changes_html(_FIXTURE_HTML)
    assert len(changes) == 3

    by_date = {c.when: c for c in changes}
    assert by_date[date(2024, 3, 15)].added == "SMCI"
    assert by_date[date(2024, 3, 15)].removed == "WHR"
    assert by_date[date(2023, 10, 2)].added == "BLDR"
    assert by_date[date(2023, 10, 2)].removed == "DXC"
    assert by_date[date(2020, 12, 21)].added == "TSLA"
    assert by_date[date(2020, 12, 21)].removed == "AIV"


def test_parse_changes_html_strips_footnotes() -> None:
    changes = parse_changes_html(_FIXTURE_HTML)
    smci_change = next(c for c in changes if c.added == "SMCI")
    # The "[1]" footnote reference should be stripped from the reason.
    assert smci_change.reason == "Market cap rebalancing"


def test_parse_changes_html_handles_empty_input() -> None:
    assert parse_changes_html("<html><body></body></html>") == []
    # No changes table present, only a constituents table.
    only_constituents = """
        <table class="wikitable"><tr><th>Symbol</th></tr><tr><td>AAPL</td></tr></table>
    """
    assert parse_changes_html(only_constituents) == []


# ------------------------------------------------------------------
# Reverse-walk reconstruction
# ------------------------------------------------------------------
def test_members_as_of_target_after_all_changes_returns_current() -> None:
    """If no changes happened after target, current set is the answer."""
    changes = [
        IndexChange(when=date(2020, 1, 1), added="A", removed="B"),
        IndexChange(when=date(2018, 6, 1), added="C", removed="D"),
    ]
    current = {"A", "C", "Z"}
    assert members_as_of(date(2024, 1, 1), changes, current) == ["A", "C", "Z"]


def test_members_as_of_undoes_one_change() -> None:
    """Walking back across one swap puts the removed ticker in, takes added out."""
    changes = [
        IndexChange(when=date(2024, 3, 15), added="SMCI", removed="WHR"),
    ]
    current = {"SMCI", "AAPL"}
    # Just before March 15, 2024: SMCI was not in, WHR was in.
    got = members_as_of(date(2024, 3, 14), changes, current)
    assert got == ["AAPL", "WHR"]


def test_members_as_of_undoes_multiple_changes_in_correct_order() -> None:
    """Reverse walk handles a ticker added-then-removed across the window."""
    changes = [
        IndexChange(when=date(2024, 6, 1), added="X", removed="Y"),  # X enters, Y leaves
        IndexChange(when=date(2023, 6, 1), added="Y", removed="X"),  # Y enters, X leaves
    ]
    current = {"X", "AAPL"}
    # Target between the two events: X is OUT, Y is IN.
    got = members_as_of(date(2023, 12, 1), changes, current)
    assert got == ["AAPL", "Y"]
    # Target before both events: X is IN (was original), Y is OUT.
    got_pre = members_as_of(date(2022, 1, 1), changes, current)
    assert got_pre == ["AAPL", "X"]


def test_members_as_of_sorts_alphabetically() -> None:
    changes: list[IndexChange] = []
    current = {"GOOG", "AAPL", "MSFT"}
    assert members_as_of(date(2024, 1, 1), changes, current) == ["AAPL", "GOOG", "MSFT"]


def test_members_as_of_target_equal_to_change_date_keeps_change_applied() -> None:
    """The change happens AT date d, so target == d means the change is in effect."""
    changes = [
        IndexChange(when=date(2024, 3, 15), added="SMCI", removed="WHR"),
    ]
    current = {"SMCI"}
    # Exactly on the change date — change is already in effect.
    assert members_as_of(date(2024, 3, 15), changes, current) == ["SMCI"]
    # One day before — change has not happened yet.
    assert members_as_of(date(2024, 3, 14), changes, current) == ["WHR"]
