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


# --- vendor volume that is already adjusted ---------------------------------
#
# EODHD stores raw prices but volume already expressed in today's shares. The
# AAPL case as stored: $645.57 on 2014-06-06 on ~335M shares, $93.70 on
# 2014-06-09 on ~300M -- no step in volume, a 7x step in price.


def _aapl_as_eodhd_stores_it():
    bars = frame([645.57, 93.70], start="2014-06-06")
    bars.index = pd.to_datetime(["2014-06-06", "2014-06-09"])
    raw_shares = [12_000_000.0, 84_000_000.0]            # what actually traded
    bars["volume"] = [raw_shares[0] * 7, raw_shares[1]]  # vendor: today's shares
    return bars, raw_shares


def test_vendor_adjusted_volume_is_not_adjusted_twice():
    """Multiplying volume that is already in post-split shares by the split
    again made pre-split AAPL look seven times as liquid as it was."""
    bars, raw = _aapl_as_eodhd_stores_it()
    split = [Split(date(2014, 6, 9), 7.0)]

    adjusted = adjust_bars(bars, split, volume_already_adjusted=True)

    assert list(adjusted["volume"]) == pytest.approx([raw[0] * 7, raw[1]])


def test_vendor_dollar_volume_is_the_money_that_actually_traded():
    """Dollar volume is what the universe's liquidity floor reads."""
    bars, raw = _aapl_as_eodhd_stores_it()
    split = [Split(date(2014, 6, 9), 7.0)]

    adjusted = adjust_bars(bars, split, volume_already_adjusted=True)
    dv = adjusted["close"] * adjusted["volume"]

    assert list(dv) == pytest.approx([645.57 * raw[0], 93.70 * raw[1]])


def test_a_split_the_run_cannot_see_does_not_move_past_liquidity():
    """The lookahead case. With the 2014 split beyond the run's horizon, the
    vendor's volume still carries it; it must be taken back out, or whether a
    stock cleared a liquidity floor in 2012 depends on a split in 2014."""
    bars, raw = _aapl_as_eodhd_stores_it()
    split = [Split(date(2014, 6, 9), 7.0)]

    adjusted = adjust_bars(
        bars, [], all_splits=split, volume_already_adjusted=True,
    )

    assert adjusted["close"].iloc[0] == pytest.approx(645.57)
    assert adjusted["volume"].iloc[0] == pytest.approx(raw[0])
    assert adjusted["close"].iloc[0] * adjusted["volume"].iloc[0] == pytest.approx(
        645.57 * raw[0]
    )


def test_a_reverse_split_does_not_make_a_small_cap_look_thin():
    """1-for-30, stored as ML's was: $0.42 on 23,767 vendor shares, which is
    ~713,000 shares actually traded. Adjusted twice, it read as $10,000 a day."""
    bars = frame([0.4195, 9.19], start="2023-04-24")
    bars.index = pd.to_datetime(["2023-04-24", "2023-04-25"])
    bars["volume"] = [23_767.0, 562_670.0]
    split = [Split(date(2023, 4, 25), 1 / 30)]

    adjusted = adjust_bars(bars, split, volume_already_adjusted=True)

    assert adjusted["close"].iloc[0] * adjusted["volume"].iloc[0] == pytest.approx(
        0.4195 * 23_767.0 * 30
    )


def test_rows_are_converted_by_their_own_source():
    """One stored symbol has bars from both vendors. Each row is converted by
    whether ITS volume was raw."""
    bars = frame([645.57, 645.0, 93.70], start="2014-06-05")
    bars.index = pd.to_datetime(["2014-06-05", "2014-06-06", "2014-06-09"])
    bars["volume"] = [12_000_000.0, 84_000_000.0, 84_000_000.0]   # raw, vendor, either
    marked = pd.Series([False, True, True], index=bars.index)

    adjusted = adjust_bars(
        bars, [Split(date(2014, 6, 9), 7.0)], volume_already_adjusted=marked,
    )

    assert list(adjusted["volume"]) == pytest.approx([84_000_000.0] * 3)
