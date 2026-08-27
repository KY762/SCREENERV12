"""A fear and greed composite over stored daily series.

The failure that matters most here is lookahead. A percentile rank is the
easiest place in this project to leak the future, because the obvious
implementation ranks each value against the whole sample -- which lets a 2013
reading know what 2015 did.
"""

from __future__ import annotations

import pandas as pd
import pytest

from screener.calc.sentiment import (
    COMPONENTS,
    fear_greed_frame,
    label_for,
    latest_reading,
    relative_return,
    trailing_percentile,
)


def _dates(n: int) -> pd.DatetimeIndex:
    return pd.bdate_range("2015-01-01", periods=n)


def test_percentile_rank_does_not_consult_the_future():
    """Truncating the series must not change any rank that came before the
    cut. Ranking against the full sample passes every other test in this file
    and silently fails this one."""
    values = pd.Series(range(400), index=_dates(400), dtype="float64")

    full = trailing_percentile(values, window=200, min_periods=50)
    truncated = trailing_percentile(values.iloc[:300], window=200, min_periods=50)

    pd.testing.assert_series_equal(full.iloc[:300], truncated)


def test_percentile_is_nan_before_enough_history():
    """A rank computed from three observations is arithmetic, not
    information. Returning 50 there would fabricate a neutral reading."""
    values = pd.Series(range(120), index=_dates(120), dtype="float64")

    ranked = trailing_percentile(values, window=100, min_periods=60)

    assert ranked.iloc[:59].isna().all()
    assert ranked.iloc[60:].notna().all()


def test_rising_series_ranks_at_the_top_and_falling_at_the_bottom():
    rising = pd.Series(range(300), index=_dates(300), dtype="float64")
    falling = pd.Series(range(300, 0, -1), index=_dates(300), dtype="float64")

    assert trailing_percentile(rising).iloc[-1] == pytest.approx(100.0)
    assert trailing_percentile(falling).iloc[-1] == pytest.approx(0.0)


def test_missing_inputs_are_reported_rather_than_defaulted_to_neutral():
    """Absent bond series must shrink the component set, not contribute 50.
    Defaulting them would drag every reading toward neutral and hide that
    two of the seven components were never computed."""
    index = _dates(400)
    metrics = pd.DataFrame(
        {
            "above_sma_200": [True] * 400,
            "pct_from_252d_high": [-0.01] * 400,
            "rvol_20": [1.0] * 400,
        },
        index=index,
    )

    frame = fear_greed_frame(metrics, benchmark=None)
    reading = latest_reading(frame)

    assert reading is not None
    assert "safe_haven" in reading.missing
    assert "junk_demand" in reading.missing
    assert "momentum" in reading.missing
    assert set(reading.components) <= set(COMPONENTS)


def test_no_inputs_returns_no_reading_rather_than_a_number():
    empty = pd.DataFrame()

    assert latest_reading(fear_greed_frame(empty)) is None


def test_relative_return_aligns_on_shared_dates_only():
    """Bond and equity series have different holidays. Subtracting them
    unaligned silently compares different days."""
    long_index = _dates(100)
    short_index = long_index[::2]

    equities = pd.Series(range(1, 101), index=long_index, dtype="float64")
    bonds = pd.Series(range(1, 51), index=short_index, dtype="float64")

    spread = relative_return(equities, bonds, window=5)

    assert spread.index.equals(short_index)


def test_bands_cover_the_whole_scale():
    """A score that falls between two bands would render as 'unknown' on the
    gauge, which is a display bug that only shows at specific values."""
    for score in (0, 12, 25, 44, 45, 54, 55, 74, 75, 99, 100):
        assert label_for(float(score)) != "unknown", score
