"""News parsing.

Small surface, but two failure modes matter: a headline with no timestamp
cannot be placed in a session, and an item mentioning several tickers is news
for each of them.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from screener.config import Settings
from screener.providers.base import ProviderError
from screener.providers.news import (
    AlpacaNewsProvider,
    headlines_by_symbol,
    parse_news,
)

PAYLOAD = {
    "news": [
        {
            "id": 40123, "headline": "Nvidia beats on data-centre revenue",
            "summary": "Revenue above consensus.", "author": "staff",
            "source": "benzinga", "url": "https://example.com/1",
            "symbols": ["NVDA", "AMD", "AVGO"],
            "created_at": "2026-08-26T20:15:00Z",
        },
        {
            "id": 40124, "headline": "Apple supplier raises guidance",
            "summary": "", "source": "benzinga", "url": "https://example.com/2",
            "symbols": ["AAPL"], "created_at": "2026-08-26T13:02:00Z",
        },
    ]
}


def test_headlines_parse():
    items = parse_news(PAYLOAD)

    assert len(items) == 2
    assert items[0].headline.startswith("Nvidia beats")
    assert items[0].symbols == ("NVDA", "AMD", "AVGO")
    assert items[0].created_at == datetime.fromisoformat("2026-08-26T20:15:00+00:00")


def test_an_item_without_a_timestamp_is_dropped():
    """It cannot be placed in a session, so it cannot inform a decision about
    one."""
    payload = {"news": [{"id": 1, "headline": "No date", "symbols": ["X"]}]}
    assert parse_news(payload) == []


def test_an_item_without_a_headline_is_dropped():
    payload = {"news": [{"id": 1, "headline": "", "created_at": "2026-08-26T13:02:00Z"}]}
    assert parse_news(payload) == []


def test_empty_payload_is_handled():
    assert parse_news({}) == []
    assert parse_news({"news": []}) == []


def test_a_multi_symbol_story_appears_under_each_symbol():
    """A story about a supplier is news for the customer too."""
    grouped = headlines_by_symbol(parse_news(PAYLOAD))

    assert set(grouped) == {"NVDA", "AMD", "AVGO", "AAPL"}
    assert grouped["AMD"][0].headline.startswith("Nvidia beats")


def test_grouping_is_newest_first():
    grouped = headlines_by_symbol(parse_news(PAYLOAD))
    nvda = grouped["NVDA"]
    assert nvda == sorted(nvda, key=lambda i: i.created_at, reverse=True)


def test_trade_date_comes_from_the_timestamp():
    item = parse_news(PAYLOAD)[0]
    assert item.trade_date == date(2026, 8, 26)


def test_missing_credentials_fail_with_an_actionable_message():
    with pytest.raises(ProviderError, match="ALPACA_API_KEY_ID"):
        AlpacaNewsProvider(Settings(alpaca_api_key_id=None, alpaca_api_secret_key=None))
