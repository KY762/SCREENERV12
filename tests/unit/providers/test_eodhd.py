"""EODHD: the delisted-coverage purchase, and the raw-price rule.

Bought for what free feeds cannot do -- serve a dead ticker's history, and
enumerate what is no longer listed. These tests pin the response format and the
two ways this adapter could quietly corrupt the database: storing adjusted
prices, or turning a quota error into an empty result.
"""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from screener.config import Settings
from screener.providers.base import BarRequest, ProviderError
from screener.providers.eodhd import EodhdProvider, _rows_to_frame, _us

SETTINGS = Settings(eodhd_api_key="test-key")

BARS = [
    # EODHD serves raw OHLC with adjusted_close alongside. The 2020 split is
    # why close and adjusted_close differ here.
    {"date": "2015-06-01", "open": 130.0, "high": 131.0, "low": 129.0,
     "close": 130.5, "adjusted_close": 32.6, "volume": 1000000},
    {"date": "2015-06-02", "open": 130.5, "high": 132.0, "low": 130.0,
     "close": 131.75, "adjusted_close": 32.9, "volume": 1200000},
]


def provider(handler) -> EodhdProvider:
    return EodhdProvider(
        SETTINGS, client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_stored_prices_are_raw_not_adjusted():
    """Non-negotiable 2. Storing adjusted_close makes stored history change
    under you at every future split; the adjusted series is derived on demand."""
    frame = _rows_to_frame("AAPL", BARS)

    assert frame.loc[("AAPL", date(2015, 6, 1)), "close"] == pytest.approx(130.5)
    assert "adjusted_close" not in frame.columns


def test_bars_are_indexed_by_symbol_and_date():
    frame = _rows_to_frame("AAPL", BARS)

    assert list(frame.index.names) == ["symbol", "date"]
    assert len(frame) == 2
    assert frame.loc[("AAPL", date(2015, 6, 2)), "volume"] == pytest.approx(1_200_000)


def test_one_unparseable_bar_does_not_lose_the_symbol():
    frame = _rows_to_frame("AAPL", [BARS[0], {"date": "2015-06-02", "open": None}])
    assert len(frame) == 1


def test_us_tickers_are_addressed_with_their_exchange_suffix():
    assert _us("aapl") == "AAPL.US"
    assert _us("BRK.B") == "BRK.B", "an explicit suffix is left alone"


def test_a_delisted_ticker_returns_its_real_history():
    """The reason for the subscription: FRC failed in 2023 and the free feeds
    return nothing for it."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/api/eod/FRC.US" in str(request.url)
        return httpx.Response(200, json=BARS)

    with provider(handler) as p:
        frame = p.get_daily_bars(
            BarRequest(symbols=("FRC",), start=date(2015, 1, 1), end=date(2015, 12, 31))
        )

    assert len(frame) == 2
    assert frame.index.get_level_values("symbol").unique().tolist() == ["FRC"]


def test_delisted_symbols_can_be_enumerated():
    """You cannot recover the missing names by querying the ones you have."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert "delisted=1" in str(request.url)
        return httpx.Response(200, json=[
            {"Code": "FRC", "Name": "First Republic Bank",
             "Exchange": "NYSE", "Type": "Common Stock"},
            {"Code": "", "Name": "junk"},
        ])

    with provider(handler) as p:
        dead = p.list_delisted()

    assert [d.symbol for d in dead] == ["FRC"], "a row with no code is dropped"
    assert dead[0].name == "First Republic Bank"


def test_asking_for_adjusted_prices_is_refused():
    with provider(lambda r: httpx.Response(200, json=BARS)) as p:
        with pytest.raises(ProviderError, match="raw prices only"):
            p.get_daily_bars(BarRequest(
                symbols=("AAPL",), start=date(2015, 1, 1), end=date(2015, 12, 31),
                adjustment="split",
            ))


@pytest.mark.parametrize(
    ("status", "message"),
    [(401, "rejected the API key"), (402, "outside the plan"), (429, "quota exhausted")],
)
def test_a_refusal_raises_rather_than_returning_nothing(status, message):
    """An empty frame would be indistinguishable from 'this ticker has no
    history', which is exactly the conclusion the subscription exists to avoid
    reaching by accident."""
    with provider(lambda r: httpx.Response(status, json={"error": "no"})) as p:
        with pytest.raises(ProviderError, match=message):
            p.get_daily_bars(BarRequest(
                symbols=("FRC",), start=date(2015, 1, 1), end=date(2015, 12, 31)
            ))


def test_no_key_is_a_clear_refusal():
    with pytest.raises(ProviderError, match="EODHD_API_KEY"):
        EodhdProvider(Settings())
