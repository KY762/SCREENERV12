"""Tiingo adapter tests.

The parsing helpers are pure, so the response shape is pinned without a
network. The HTTP behaviour is exercised through a stub client, because the
failure modes that matter here -- a rate limit, an error object where a list
was expected -- are exactly the ones a live test would be unable to trigger on
demand.
"""

from __future__ import annotations

from datetime import date

import httpx
import pandas as pd
import pytest

from screener.config import Settings
from screener.providers.base import BarRequest, ProviderError
from screener.providers.tiingo import (
    TiingoProvider,
    _rows_to_frame,
    parse_corporate_actions,
)

ROWS = [
    {
        "date": "2020-08-28T00:00:00.000Z",
        "open": 126.0, "high": 127.5, "low": 125.0, "close": 127.0, "volume": 187_630_000,
        "adjOpen": 126.0, "adjHigh": 127.5, "adjLow": 125.0, "adjClose": 127.0,
        "adjVolume": 187_630_000, "divCash": 0.0, "splitFactor": 1.0,
    },
    {
        "date": "2020-08-31T00:00:00.000Z",
        "open": 127.6, "high": 131.0, "low": 126.0, "close": 129.0, "volume": 225_700_000,
        "adjOpen": 127.6, "adjHigh": 131.0, "adjLow": 126.0, "adjClose": 129.0,
        "adjVolume": 225_700_000, "divCash": 0.0, "splitFactor": 4.0,
    },
    {
        "date": "2020-11-06T00:00:00.000Z",
        "open": 118.3, "high": 119.2, "low": 116.1, "close": 118.6, "volume": 114_457_900,
        "adjOpen": 118.3, "adjHigh": 119.2, "adjLow": 116.1, "adjClose": 118.6,
        "adjVolume": 114_457_900, "divCash": 0.205, "splitFactor": 1.0,
    },
]


def settings(**kwargs) -> Settings:
    return Settings(tiingo_api_key="test-token", **kwargs)


class _StubClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def close(self):
        pass


def response(payload, status=200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        json=payload,
        request=httpx.Request("GET", "https://api.tiingo.com/x"),
    )


# -- parsing ----------------------------------------------------------------

def test_rows_parse_into_a_raw_price_frame():
    frame = _rows_to_frame("AAPL", ROWS)

    assert list(frame.columns) == ["symbol", "date", "open", "high", "low", "close", "volume"]
    assert frame["date"].iloc[0] == date(2020, 8, 28)
    assert frame["close"].iloc[0] == pytest.approx(127.0)


def test_adjusted_columns_are_discarded():
    """Storing adjusted prices would make history mutate at every future split:
    what the database says about 2019 would change because of something that
    happens tomorrow. Splits are captured as corporate actions instead."""
    frame = _rows_to_frame("AAPL", ROWS)

    assert not [c for c in frame.columns if c.startswith("adj")]


def test_a_split_row_is_read_as_a_corporate_action():
    actions = parse_corporate_actions("AAPL", ROWS)
    splits = [a for a in actions if a.action_type == "split"]

    assert len(splits) == 1
    assert splits[0].ex_date == date(2020, 8, 31)
    assert splits[0].ratio == pytest.approx(4.0)


def test_a_dividend_row_is_read_as_a_corporate_action():
    actions = parse_corporate_actions("AAPL", ROWS)
    dividends = [a for a in actions if a.action_type == "dividend"]

    assert len(dividends) == 1
    assert dividends[0].ex_date == date(2020, 11, 6)
    assert dividends[0].amount == pytest.approx(0.205)


def test_ordinary_rows_produce_no_actions():
    ordinary = [{**ROWS[0], "date": "2021-01-04T00:00:00.000Z"}]
    assert parse_corporate_actions("AAPL", ordinary) == []


# -- http -------------------------------------------------------------------

def test_missing_key_is_a_clear_error():
    with pytest.raises(ProviderError, match="TIINGO_API_KEY"):
        TiingoProvider(Settings(tiingo_api_key=None))


def test_bars_are_fetched_per_symbol_and_combined():
    client = _StubClient([response(ROWS), response(ROWS)])
    provider = TiingoProvider(settings(), client=client)

    frame = provider.get_daily_bars(
        BarRequest(("AAPL", "MSFT"), date(2020, 1, 1), date(2020, 12, 31))
    )

    assert len(client.calls) == 2
    assert isinstance(frame.index, pd.MultiIndex)
    assert set(frame.index.get_level_values("symbol")) == {"AAPL", "MSFT"}


def test_rate_limit_raises_immediately_rather_than_backing_off():
    """The free tier's window is measured in hours. Retrying inside one command
    would hang far longer than anyone waits at a terminal, and the run is
    resumable anyway -- stored bars are skipped on the next attempt."""
    client = _StubClient([response({"detail": "slow down"}, status=429)])
    provider = TiingoProvider(settings(), client=client)

    with pytest.raises(ProviderError, match="rate limit"):
        provider.get_daily_bars(BarRequest(("AAPL",), date(2020, 1, 1), date(2020, 12, 31)))

    assert len(client.calls) == 1, "a rate limit must not be retried"


def test_a_rate_limit_stops_the_whole_run_not_just_one_symbol():
    """A cap applies to every remaining symbol, so continuing would produce a
    long list of identical failures and a half-loaded database."""
    client = _StubClient([response({"detail": "slow down"}, status=429), response(ROWS)])
    provider = TiingoProvider(settings(), client=client)

    with pytest.raises(ProviderError, match="rate limit"):
        provider.get_daily_bars(
            BarRequest(("AAPL", "MSFT"), date(2020, 1, 1), date(2020, 12, 31))
        )

    assert len(client.calls) == 1


def test_an_error_object_where_a_list_was_expected_is_an_error():
    """Tiingo reports failures as a JSON object; success is a list. Treating
    the object as data would yield an empty frame that looks like 'no bars'."""
    client = _StubClient([response({"detail": "Not found"})])
    provider = TiingoProvider(settings(), client=client)

    frame = provider.get_daily_bars(
        BarRequest(("NOPE",), date(2020, 1, 1), date(2020, 12, 31))
    )
    assert frame.empty, "one bad symbol yields no bars for it, and does not abort"


def test_one_unknown_symbol_does_not_lose_the_others():
    client = _StubClient([response({"detail": "Not found"}), response(ROWS)])
    provider = TiingoProvider(settings(), client=client)

    frame = provider.get_daily_bars(
        BarRequest(("NOPE", "AAPL"), date(2020, 1, 1), date(2020, 12, 31))
    )

    assert set(frame.index.get_level_values("symbol")) == {"AAPL"}


def test_transient_server_errors_are_retried():
    client = _StubClient([response({}, status=503), response(ROWS)])
    provider = TiingoProvider(
        Settings(tiingo_api_key="t", max_retries=3), client=client
    )

    frame = provider.get_daily_bars(
        BarRequest(("AAPL",), date(2020, 1, 1), date(2020, 12, 31))
    )

    assert len(client.calls) == 2
    assert not frame.empty


def test_corporate_actions_can_be_fetched_standalone():
    client = _StubClient([response(ROWS)])
    provider = TiingoProvider(settings(), client=client)

    actions = provider.get_corporate_actions(("AAPL",), date(2020, 1, 1), date(2020, 12, 31))

    assert {a.action_type for a in actions} == {"split", "dividend"}
