"""Alpaca response-parsing tests.

The parsers are deliberately pure functions so the wire format can be pinned
down without a network, an API key, or a live account. If Alpaca changes its
payload shape, these fail immediately rather than producing subtly wrong bars.
"""

from datetime import date

import pandas as pd
import pytest

from screener.providers.alpaca import _bars_to_frame, _empty_bars, _parse_corporate_actions


def test_bars_to_frame_maps_alpacas_single_letter_keys():
    payload = [
        {"t": "2024-01-02T05:00:00Z", "o": 187.15, "h": 188.44, "l": 183.89,
         "c": 185.64, "v": 82488700, "n": 1, "vw": 185.9},
        {"t": "2024-01-03T05:00:00Z", "o": 184.22, "h": 185.88, "l": 183.43,
         "c": 184.25, "v": 58414500, "n": 1, "vw": 184.6},
    ]
    frame = _bars_to_frame("AAPL", payload)

    assert list(frame.columns) == ["symbol", "date", "open", "high", "low", "close", "volume"]
    assert frame["symbol"].tolist() == ["AAPL", "AAPL"]
    assert frame["open"].iloc[0] == pytest.approx(187.15)
    assert frame["close"].iloc[1] == pytest.approx(184.25)
    assert frame["volume"].iloc[0] == pytest.approx(82_488_700)


def test_bars_to_frame_reduces_timestamps_to_trading_dates():
    """Alpaca stamps daily bars at 05:00Z. Keeping the timestamp would make every
    date comparison timezone-sensitive; the trading DATE is what the platform
    reasons about."""
    frame = _bars_to_frame(
        "SPY", [{"t": "2024-03-15T04:00:00Z", "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 10}]
    )
    assert frame["date"].iloc[0] == date(2024, 3, 15)
    assert not isinstance(frame["date"].iloc[0], pd.Timestamp)


def test_bars_to_frame_ignores_unused_fields():
    """'n' (trade count) and 'vw' (VWAP) are dropped. Storing fields nothing
    reads is how schemas rot."""
    frame = _bars_to_frame(
        "MSFT", [{"t": "2024-01-02T05:00:00Z", "o": 1, "h": 2, "l": 0.5,
                  "c": 1.5, "v": 10, "n": 999, "vw": 1.23}]
    )
    assert "n" not in frame.columns and "vw" not in frame.columns


def test_empty_bars_has_the_same_shape_as_a_real_result():
    """Callers must be able to concat or index an empty result without a special
    case. A differently-shaped empty frame is a crash waiting for a quiet day."""
    empty = _empty_bars()
    assert empty.empty
    assert empty.index.names == ["symbol", "date"]
    assert list(empty.columns) == ["open", "high", "low", "close", "volume"]


def test_parse_forward_split_computes_ratio():
    """A 4-for-1 split: old_rate 1, new_rate 4 -> ratio 4.0."""
    payload = {
        "corporate_actions": {
            "forward_splits": [
                {"symbol": "AAPL", "ex_date": "2020-08-31", "old_rate": 1, "new_rate": 4}
            ]
        }
    }
    actions = _parse_corporate_actions(payload)
    assert len(actions) == 1
    a = actions[0]
    assert (a.symbol, a.action_type, a.ex_date) == ("AAPL", "split", date(2020, 8, 31))
    assert a.ratio == pytest.approx(4.0)


def test_parse_reverse_split_yields_a_fractional_ratio():
    """A 1-for-10 reverse split: old_rate 10, new_rate 1 -> ratio 0.1."""
    payload = {
        "corporate_actions": {
            "reverse_splits": [
                {"symbol": "XYZ", "ex_date": "2023-05-01", "old_rate": 10, "new_rate": 1}
            ]
        }
    }
    assert _parse_corporate_actions(payload)[0].ratio == pytest.approx(0.1)


def test_parse_cash_dividend():
    payload = {
        "corporate_actions": {
            "cash_dividends": [{"symbol": "KO", "ex_date": "2024-03-15", "rate": 0.485}]
        }
    }
    a = _parse_corporate_actions(payload)[0]
    assert (a.symbol, a.action_type) == ("KO", "dividend")
    assert a.amount == pytest.approx(0.485)
    assert a.ratio is None


def test_parse_handles_missing_and_empty_sections():
    assert _parse_corporate_actions({}) == []
    assert _parse_corporate_actions({"corporate_actions": {}}) == []
    assert _parse_corporate_actions({"corporate_actions": {"forward_splits": []}}) == []
