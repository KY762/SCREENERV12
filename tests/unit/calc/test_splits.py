"""Split adjustment.

What breaks if these fail: every return in the project. `price_daily` holds raw
prices, so an unadjusted series reads Apple's 2014 7-for-1 split as a -86%
one-day loss and Citigroup's 2011 1-for-10 reverse split as a +900% gain. A
momentum rule then ranks Apple last and a distressed bank first, which is the
hypothesis inverted rather than merely noisy.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from screener.calc.splits import Split, adjust_bars, cumulative_factor


def frame(closes, start="2014-06-02"):
    n = len(closes)
    idx = pd.date_range(start, periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": np.array(closes, dtype="float64"),
            "high": np.array(closes, dtype="float64") * 1.01,
            "low": np.array(closes, dtype="float64") * 0.99,
            "close": np.array(closes, dtype="float64"),
            "volume": np.full(n, 1_000_000.0),
        },
        index=idx,
    )


# --- the factor ------------------------------------------------------------


def test_no_splits_leaves_everything_alone():
    """The common path. Most symbols never split, and a bug here would touch
    every one of them."""
    bars = frame([100.0, 101.0, 102.0])

    assert adjust_bars(bars, []).equals(bars)


def test_only_bars_before_the_ex_date_are_scaled():
    """`ex_date` is the first day quoted at the NEW price. Verified against
    stored data: AAPL closed 645.57 on 2014-06-06 and 93.70 on 2014-06-09, and
    645.57 / 7 = 92.2. Scaling the ex-date bar too would re-break the series."""
    idx = pd.to_datetime(["2014-06-05", "2014-06-06", "2014-06-09", "2014-06-10"])
    factor = cumulative_factor([Split(date(2014, 6, 9), 7.0)], idx)

    assert list(factor) == [7.0, 7.0, 1.0, 1.0]


def test_factors_compound_across_several_splits():
    """AAPL split 7-for-1 in 2014 and 4-for-1 in 2020, so a 2012 bar carries
    both. Applying only the nearest one leaves a 4x step in 2020."""
    idx = pd.to_datetime(["2012-01-03", "2015-01-02", "2021-01-04"])
    factor = cumulative_factor(
        [Split(date(2014, 6, 9), 7.0), Split(date(2020, 8, 31), 4.0)], idx
    )

    assert list(factor) == [28.0, 4.0, 1.0]


# --- the adjustment --------------------------------------------------------


def test_a_forward_split_stops_being_a_crash():
    """The Apple case. Raw, this is a -86% one-day return."""
    bars = frame([700.0, 100.0], start="2014-06-06")
    bars.index = pd.to_datetime(["2014-06-06", "2014-06-09"])

    adjusted = adjust_bars(bars, [Split(date(2014, 6, 9), 7.0)])
    closes = adjusted["close"]

    assert closes.iloc[0] == pytest.approx(100.0)
    assert closes.iloc[1] / closes.iloc[0] - 1 == pytest.approx(0.0)


def test_a_reverse_split_stops_being_a_moonshot():
    """The Citigroup case: 1-for-10 on 2011-05-09, raw a +900% one-day gain,
    and the single largest 'momentum' signal in the development split."""
    bars = frame([4.5, 45.0], start="2011-05-06")
    bars.index = pd.to_datetime(["2011-05-06", "2011-05-09"])

    adjusted = adjust_bars(bars, [Split(date(2011, 5, 9), 0.1)])
    closes = adjusted["close"]

    assert closes.iloc[0] == pytest.approx(45.0)
    assert closes.iloc[1] / closes.iloc[0] - 1 == pytest.approx(0.0)


def test_the_most_recent_bar_is_the_price_actually_traded():
    """Back-adjusted, not forward-adjusted: history is scaled to meet today,
    so sizing and stops on recent data use real prices."""
    bars = frame([700.0, 100.0, 101.0], start="2014-06-06")
    bars.index = pd.to_datetime(["2014-06-06", "2014-06-09", "2014-06-10"])

    adjusted = adjust_bars(bars, [Split(date(2014, 6, 9), 7.0)])

    assert adjusted["close"].iloc[-1] == pytest.approx(101.0)


def test_every_price_column_moves_together():
    """Adjusting close but not high would put the high below the close on the
    ex-date, and the stop logic reads highs and lows."""
    bars = frame([700.0, 100.0], start="2014-06-06")
    bars.index = pd.to_datetime(["2014-06-06", "2014-06-09"])

    adjusted = adjust_bars(bars, [Split(date(2014, 6, 9), 7.0)])

    assert adjusted["high"].iloc[0] == pytest.approx(101.0)
    assert adjusted["low"].iloc[0] == pytest.approx(99.0)
    assert adjusted["open"].iloc[0] == pytest.approx(100.0)
    assert (adjusted["high"] >= adjusted["close"]).all()
    assert (adjusted["low"] <= adjusted["close"]).all()


def test_volume_moves_the_other_way():
    """The same traded value is a different share count on each side of a
    split. Leaving volume raw puts a 7x step into every liquidity measure on
    the ex-date, and dollar volume is what the universe filter reads."""
    bars = frame([700.0, 100.0], start="2014-06-06")
    bars.index = pd.to_datetime(["2014-06-06", "2014-06-09"])

    adjusted = adjust_bars(bars, [Split(date(2014, 6, 9), 7.0)])

    assert adjusted["volume"].iloc[0] == pytest.approx(7_000_000.0)


def test_dollar_volume_is_unchanged_by_the_adjustment():
    """Price x shares is the same traded value on either side of a split, so
    dividing price and multiplying volume has to cancel exactly.

    This is why the liquidity evidence behind the quarantine survived the
    discovery that splits were unadjusted: median dollar volume during index
    membership means the same thing before and after this fix.
    """
    bars = frame([700.0, 100.0], start="2014-06-06")
    bars.index = pd.to_datetime(["2014-06-06", "2014-06-09"])
    raw_dv = bars["close"] * bars["volume"]

    adjusted = adjust_bars(bars, [Split(date(2014, 6, 9), 7.0)])
    adjusted_dv = adjusted["close"] * adjusted["volume"]

    assert list(adjusted_dv) == pytest.approx(list(raw_dv))


def test_the_input_frame_is_not_modified():
    """Bars are cached and shared between cells of a surface sweep. Adjusting
    in place would apply the factor once per cell."""
    bars = frame([700.0, 100.0], start="2014-06-06")
    bars.index = pd.to_datetime(["2014-06-06", "2014-06-09"])
    before = bars["close"].copy()

    adjust_bars(bars, [Split(date(2014, 6, 9), 7.0)])

    assert bars["close"].equals(before)


def test_a_nonpositive_ratio_is_ignored_rather_than_dividing_by_zero():
    """A bad vendor row should not silently produce infinities in a price
    series that then ranks first on every momentum screen."""
    bars = frame([100.0, 101.0])

    assert adjust_bars(bars, [Split(date(2014, 6, 3), 0.0)]).equals(bars)
