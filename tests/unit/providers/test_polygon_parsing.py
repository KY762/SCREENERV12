"""Polygon response parsing.

The adapter exists for one reason: `universe coverage` measured acquisitions
6/6 present and failures 0/6 on the free feeds. Acquisitions end at a premium
and failures near zero, so the data keeps every good ending and loses every bad
one, biasing every backtested return upward.

Parsing lives at module level so these run without a key or a network.
"""

from __future__ import annotations

from datetime import date

import pytest

from screener.providers.base import BarRequest, ProviderError
from screener.providers.polygon import (
    TickerStatus,
    _bar_date,
    _parse_dividend,
    _parse_split,
    _parse_status,
    _rows_to_frame,
)


def test_split_ratio_is_to_over_from():
    """A 2-for-1 must be 2.0. Inverting it halves every pre-split price instead
    of doubling it, which silently corrupts all history before the split."""
    action = _parse_split("AAPL", {
        "execution_date": "2020-08-31", "split_to": 4, "split_from": 1,
    })

    assert action is not None
    assert action.action_type == "split"
    assert action.ratio == pytest.approx(4.0)
    assert action.ex_date == date(2020, 8, 31)


def test_reverse_split_is_a_fraction_not_an_error():
    """A 1-for-10 reverse split is ratio 0.1. Distressed companies do these,
    and they are exactly the population the delisted feed exists to recover."""
    action = _parse_split("XYZ", {
        "execution_date": "2023-05-01", "split_to": 1, "split_from": 10,
    })

    assert action.ratio == pytest.approx(0.1)


def test_malformed_actions_are_skipped_not_raised():
    """One bad row must not abort a backfill of thousands of symbols."""
    assert _parse_split("X", {"execution_date": "2020-01-01", "split_to": 1}) is None
    assert _parse_split("X", {"split_to": 2, "split_from": 1}) is None
    assert _parse_split("X", {
        "execution_date": "2020-01-01", "split_to": 1, "split_from": 0,
    }) is None
    assert _parse_dividend("X", {"ex_dividend_date": "2020-01-01"}) is None
    assert _parse_dividend("X", {"cash_amount": 0.5}) is None


def test_dividend_carries_amount_not_ratio():
    action = _parse_dividend("KO", {
        "ex_dividend_date": "2024-03-15", "cash_amount": 0.485,
    })

    assert action.action_type == "dividend"
    assert action.amount == pytest.approx(0.485)
    assert action.ratio is None


def test_delisted_ticker_reports_the_date_it_stopped():
    """The whole point. SIVB failed in March 2023; a feed that serves it as
    active is the failure mode `universe coverage` flagged as suspect."""
    status = _parse_status("SIVB", {
        "ticker": "SIVB", "active": False,
        "delisted_utc": "2023-04-26T00:00:00Z", "name": "SVB Financial Group",
    })

    assert status.active is False
    assert status.delisted_on == date(2023, 4, 26)


def test_absent_delisting_date_is_none_not_a_claim_of_being_listed():
    """`delisted_on is None` covers both an active ticker and one whose date
    the provider lacks. Treating None as proof of continued listing would
    reintroduce exactly the survivorship assumption being removed."""
    inactive = _parse_status("X", {"ticker": "X", "active": False})

    assert inactive.active is False
    assert inactive.delisted_on is None


def test_bars_are_indexed_by_symbol_and_date():
    frame = _rows_to_frame("FRC", [
        {"t": 1_672_808_400_000, "o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5, "v": 100.0},
    ])

    assert list(frame.index.names) == ["symbol", "date"]
    assert frame.iloc[0]["close"] == pytest.approx(1.5)
    assert frame.iloc[0]["volume"] == pytest.approx(100.0)


def test_rows_without_a_timestamp_are_dropped():
    """A row with no date cannot be placed in a time series. Keeping it with a
    fabricated date would put a bar on a day that never traded."""
    frame = _rows_to_frame("X", [
        {"o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5, "v": 10.0},
    ])

    assert frame.empty


def test_epoch_milliseconds_convert_to_the_trading_date():
    assert _bar_date(1_672_808_400_000) == date(2023, 1, 4)


def test_adjusted_bars_are_refused():
    """Non-negotiable 2: raw prices only. Storing pre-adjusted bars makes
    history mutate at every future split."""
    from screener.providers.polygon import PolygonProvider

    request = BarRequest(("AAPL",), date(2020, 1, 1), date(2020, 2, 1), "split")

    with pytest.raises(ProviderError, match="raw"):
        PolygonProvider.get_daily_bars(object(), request)


def test_ticker_status_is_immutable():
    """Listing status is a fact about the past; a caller must not edit it."""
    status = TickerStatus("BBBY", active=False, delisted_on=date(2023, 5, 3))

    with pytest.raises(AttributeError):
        status.active = True
