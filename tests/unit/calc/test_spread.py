"""Effective spread from daily highs and lows.

What breaks if these fail: the cost model. Every result in this project has
assumed 5 basis points a side, a constant nobody measured. On the mid and small
caps the universe is moving to, the real figure decides whether an edge exists
rather than trimming it -- NBR estimates at 36.5bp on this database, which is
4.6% a year of drag at a 20-day hold and 1.5% at 63.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from screener.calc.spread import (
    annual_drag,
    corwin_schultz,
    round_trip_cost,
    typical_spread,
)


def frame(highs, lows, closes=None):
    n = len(highs)
    idx = pd.date_range("2015-01-02", periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": np.asarray(lows, dtype="float64"),
            "high": np.asarray(highs, dtype="float64"),
            "low": np.asarray(lows, dtype="float64"),
            "close": np.asarray(closes if closes is not None else highs, dtype="float64"),
            "volume": np.full(n, 1e6),
        },
        index=idx,
    )


def test_the_first_day_has_no_estimate():
    """The estimator compares two consecutive sessions, so day one cannot have
    one. Returning 0 there instead of NaN would drag every average down."""
    out = corwin_schultz(frame([101, 101, 101], [99, 99, 99]))

    assert np.isnan(out.iloc[0])
    assert out.notna().sum() == 2


def test_a_frame_too_short_to_estimate_returns_nan_not_zero():
    out = corwin_schultz(frame([100.0], [99.0]))

    assert len(out) == 1
    assert np.isnan(out.iloc[0])


def test_a_wider_daily_range_for_the_same_two_day_range_reads_as_more_spread():
    """The whole idea: variance scales with time and the spread does not, so
    when two single-day ranges are wide but the two-day range is no wider, the
    excess is spread rather than volatility."""
    # Same two-day envelope in both, but the second has wider single days.
    tight = corwin_schultz(frame([100.5, 100.5], [99.5, 99.5], [100, 100]))
    wide = corwin_schultz(frame([101.0, 101.0], [99.0, 99.0], [100, 100]))

    assert wide.iloc[1] > tight.iloc[1]


def test_negative_estimates_are_floored_not_dropped():
    """The estimator is noisy day to day and negatives are expected. Dropping
    them keeps only the upward errors and biases the mean high -- which would
    make costs look worse than they are, the wrong direction for a number used
    to decide whether an edge survives."""
    # A two-day range much wider than the single days drives alpha negative.
    out = corwin_schultz(frame([100.1, 105.0], [100.0, 104.9], [100.05, 104.95]))

    assert (out.dropna() >= 0).all()


def test_an_overnight_gap_would_otherwise_report_no_cost_at_all():
    """The direction here is the opposite of the intuitive one, and this test
    is why the module docstring had it backwards until it ran.

    A gap inflates the TWO-DAY range while leaving the single-day ranges alone
    -- which is precisely the signature the estimator reads as "no spread". The
    estimate goes negative and floors at zero, so an uncorrected gapping
    session reports no trading cost whatsoever. A momentum rule buys names that
    have just gapped on news, so those are the costs that would vanish.

    Same bars both ways: a two-point band, then a twenty-point gap up.
    """
    highs = [101.0, 121.0]
    lows = [99.0, 119.0]
    closes = [99.0, 119.0]

    corrected = corwin_schultz(frame(highs, lows, closes), adjust_for_gaps=True)
    raw = corwin_schultz(frame(highs, lows, closes), adjust_for_gaps=False)

    assert raw.iloc[1] == 0.0, "uncorrected, the gap hides the spread entirely"
    assert corrected.iloc[1] > 0.01, "corrected, the band's real spread shows"


def test_typical_spread_is_a_median_not_a_mean():
    """One halted or gapping session should not set the cost assumed for a
    month of trading."""
    highs = [100.5] * 20 + [140.0] + [100.5] * 5
    lows = [99.5] * 20 + [60.0] + [99.5] * 5
    out = typical_spread(frame(highs, lows), window=21)

    assert out.dropna().max() < 0.05, "one wild session should not dominate"


# --- the arithmetic that decides whether an edge survives -------------------


def test_a_round_trip_charges_one_spread_not_two():
    """The quoted spread already spans both sides: buying at the ask and
    selling at the bid gives up one spread in total. Charging two is the most
    common way this arithmetic goes wrong, and it would double every cost
    estimate in the project."""
    assert round_trip_cost(0.004) == pytest.approx(0.004)
    assert round_trip_cost(0.004, slippage_bps=5.0) == pytest.approx(0.005)


def test_drag_scales_with_how_often_you_turn_over():
    """The finding that matters: the same spread costs about three times as
    much at a 20-day hold as at 63."""
    spread = 0.00365                      # NBR, measured on this database

    fast = annual_drag(spread, 20)
    slow = annual_drag(spread, 63)

    assert fast == pytest.approx(0.046, abs=0.002)
    assert slow == pytest.approx(0.0146, abs=0.002)
    assert fast / slow == pytest.approx(63 / 20, rel=0.01)


def test_a_zero_hold_is_undefined_rather_than_infinite():
    assert np.isnan(annual_drag(0.004, 0))
