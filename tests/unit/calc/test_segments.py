"""A long hole in trading ends a series.

What breaks if these fail: a ticker that changed hands is read as one
security, so a momentum reading on the new holder is measured from the old
holder's price, and a position in the old one is next priced on the new one.
"""

from __future__ import annotations

import pandas as pd

from screener.calc.segments import (
    MAX_GAP_DAYS,
    base_ticker,
    segment_keys,
    split_at_gaps,
)


def _bars(dates, volume=1_000_000.0, price=10.0):
    idx = pd.to_datetime(dates)
    n = len(idx)
    vol = volume if isinstance(volume, list) else [volume] * n
    return pd.DataFrame(
        {"open": [price] * n, "high": [price] * n, "low": [price] * n,
         "close": [price] * n, "volume": vol},
        index=idx,
    )


def _handover(gap_days):
    """Twenty sessions, a hole of `gap_days`, twenty more."""
    first = pd.bdate_range("2010-01-04", periods=20)
    resume = first[-1] + pd.Timedelta(days=gap_days)
    second = pd.bdate_range(resume, periods=20)
    return _bars(list(first) + list(second))


def test_a_hole_of_the_threshold_cuts_the_series():
    pieces = split_at_gaps(_handover(MAX_GAP_DAYS))

    assert [len(p) for p in pieces] == [20, 20]


def test_a_hole_one_day_short_of_the_threshold_does_not():
    """A trading halt of the same company is not a change of hands; cutting it
    would throw away the warm-up of every indicator for nothing."""
    assert len(split_at_gaps(_handover(MAX_GAP_DAYS - 1))) == 1


def test_an_unbroken_series_comes_back_whole():
    frame = _bars(pd.bdate_range("2010-01-04", periods=300))

    pieces = split_at_gaps(frame)

    assert len(pieces) == 1
    assert pieces[0].equals(frame)


def test_every_bar_lands_in_exactly_one_piece():
    frame = _handover(400)

    pieces = split_at_gaps(frame)

    assert sum(len(p) for p in pieces) == len(frame)
    assert pd.concat(pieces).index.equals(frame.index)


def test_zero_volume_bars_inside_the_hole_stay_with_the_series_that_stopped():
    """They are the frozen tail of the security that stopped trading. Moving
    them to the next series would hand the new holder the old one's last price
    and take the no_volume exit away from a position in the old one."""
    live = list(pd.bdate_range("2010-01-04", periods=20))
    frozen = list(pd.bdate_range(live[-1] + pd.Timedelta(days=1), periods=60))
    later = list(pd.bdate_range(frozen[-1] + pd.Timedelta(days=5), periods=20))
    frame = _bars(live + frozen + later, volume=[1e6] * 20 + [0.0] * 60 + [1e6] * 20)

    pieces = split_at_gaps(frame)

    assert [len(p) for p in pieces] == [80, 20]
    assert (pieces[0]["volume"].iloc[20:] == 0).all()


def test_placeholder_bars_do_not_hide_a_hole():
    """Measured on TRADED bars. A frozen tail filling the calendar is still a
    security that did not trade for months."""
    live = list(pd.bdate_range("2010-01-04", periods=20))
    frozen = list(pd.bdate_range(live[-1] + pd.Timedelta(days=1), periods=100))
    later = list(pd.bdate_range(frozen[-1] + pd.Timedelta(days=1), periods=20))
    frame = _bars(live + frozen + later, volume=[1e6] * 20 + [0.0] * 100 + [1e6] * 20)

    assert len(split_at_gaps(frame)) == 2


def test_the_latest_series_keeps_the_ticker_and_earlier_ones_carry_their_last_trade():
    """The latest series is what a live screen sees today, so it keeps the name
    anything outside a backtest will look it up by."""
    pieces = split_at_gaps(_handover(4000))

    keys = segment_keys("JAVA", pieces)

    assert keys[-1] == "JAVA"
    assert keys[0] == f"JAVA@{pieces[0].index[-1]:%Y-%m-%d}"


def test_an_earlier_series_is_named_for_its_last_trade_not_its_frozen_tail():
    live = list(pd.bdate_range("2010-01-04", periods=20))
    frozen = list(pd.bdate_range(live[-1] + pd.Timedelta(days=1), periods=60))
    later = list(pd.bdate_range(frozen[-1] + pd.Timedelta(days=5), periods=20))
    frame = _bars(live + frozen + later, volume=[1e6] * 20 + [0.0] * 60 + [1e6] * 20)

    keys = segment_keys("DEAD", split_at_gaps(frame))

    assert keys[0] == f"DEAD@{live[-1]:%Y-%m-%d}"


def test_base_ticker_strips_only_the_segment_mark():
    assert base_ticker("JAVA@2010-01-26") == "JAVA"
    assert base_ticker("JAVA") == "JAVA"
    assert base_ticker("BRK.B") == "BRK.B"
    assert base_ticker("TMC_OLD2") == "TMC_OLD2"
