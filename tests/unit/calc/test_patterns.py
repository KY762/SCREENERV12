"""Geometry tests for FVG, IFVG, swings, and liquidity sweeps.

Each fixture is constructed so the expected gap or pivot can be verified by
reading the numbers, not by trusting the implementation.
"""

import numpy as np
import pandas as pd
import pytest

from screener.calc import patterns as pat


def _frame(rows):
    return pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"]).astype(float)


def test_bullish_fvg_exact_geometry():
    """high[0]=100 < low[2]=102  ->  gap zone [100, 102], size 2."""
    df = _frame([
        [100, 100,  95,  98, 1000],
        [ 98, 110,  97, 108, 3000],
        [108, 115, 102, 112, 2000],
    ])
    gaps = pat.find_gaps(df, "bullish")
    assert len(gaps) == 1
    g = gaps[0]
    assert (g.formation_idx, g.bottom, g.top) == (2, 100.0, 102.0)
    assert g.size == pytest.approx(2.0)


def test_bearish_fvg_exact_geometry():
    """low[0]=95 > high[2]=92  ->  gap zone [92, 95], size 3."""
    df = _frame([
        [100, 100, 95, 96, 1000],
        [ 96,  99, 88, 90, 3000],
        [ 90,  92, 85, 87, 2000],
    ])
    gaps = pat.find_gaps(df, "bearish")
    assert len(gaps) == 1
    g = gaps[0]
    assert (g.formation_idx, g.bottom, g.top) == (2, 92.0, 95.0)
    assert g.size == pytest.approx(3.0)


def test_touching_bars_are_not_a_gap():
    """high[0] == low[2] leaves no untraded zone. Strict inequality is required."""
    df = _frame([
        [100, 100,  95,  98, 1000],
        [ 98, 110,  97, 108, 3000],
        [108, 115, 100, 112, 2000],
    ])
    assert pat.find_gaps(df, "bullish") == []


def test_displacement_body_vs_range_diverge_on_a_doji():
    """A long-wicked doji has large RANGE and near-zero BODY. The two measures
    must disagree here -- that divergence is the whole reason the choice matters."""
    rows = [[100, 101, 99, 100, 1000]] * 15
    rows.append([100, 120, 80, 100.5, 1000])   # huge range, tiny body
    rows.append([100, 101, 99, 100, 1000])
    df = _frame(rows)
    body = pat.displacement_ratio(df, "body", 14)
    rng = pat.displacement_ratio(df, "range", 14)
    assert rng.iloc[15] > 10 * body.iloc[15]


def test_swing_low_pivot_located_correctly():
    """lows [10, 8, 5, 9, 11] with left=right=2 -> pivot at index 2."""
    df = _frame([
        [10, 12, 10, 11, 100],
        [ 9, 10,  8,  9, 100],
        [ 7,  8,  5,  6, 100],
        [ 7, 10,  9, 10, 100],
        [10, 13, 11, 12, 100],
    ])
    piv = pat.swing_low_pivots(df, left=2, right=2)
    assert list(np.flatnonzero(piv.to_numpy())) == [2]


def test_confirmed_swing_low_is_delayed_by_right_bars():
    """The pivot sits at index 2 but is only knowable at index 2+right=4.
    Anything earlier would be lookahead."""
    df = _frame([
        [10, 12, 10, 11, 100],
        [ 9, 10,  8,  9, 100],
        [ 7,  8,  5,  6, 100],
        [ 7, 10,  9, 10, 100],
        [10, 13, 11, 12, 100],
    ])
    confirmed = pat.confirmed_swing_low_price(df, left=2, right=2)
    assert confirmed.iloc[:4].isna().all(), "pivot must not appear before confirmation"
    assert confirmed.iloc[4] == pytest.approx(5.0)


@pytest.mark.parametrize(
    "kind,expected_col",
    [
        ("prior_day", "liq_ref_prior_day"),
        ("n_bar", "liq_ref_3bar"),
        ("prior_week", "liq_ref_prior_week"),
    ],
)
def test_liquidity_reference_excludes_current_bar(kind, expected_col):
    """The reference must pre-exist the sweep, or the test is circular."""
    df = _frame([[10, 12, 10, 11, 100]] * 4 + [[10, 12, 1, 11, 100]])
    ref = pat.liquidity_reference(df, kind, n=3)
    assert ref.name == expected_col
    assert ref.iloc[4] != 1.0, "current bar's own low leaked into its reference"


def test_sweep_reclaim_requires_both_conditions():
    """reference = min of prior 3 lows = 10.
    t3 sweeps (low 9 < 10) and reclaims (close 11 > 10) -> True.
    t4 sweeps but closes below -> False. Reclaim is what separates this from a
    falling knife."""
    df = _frame([
        [10, 13, 10, 12, 100],
        [12, 14, 11, 13, 100],
        [13, 15, 12, 14, 100],
        [13, 14,  9, 11, 100],
        [11, 12,  8,  8, 100],
    ])
    ref = pat.liquidity_reference(df, "n_bar", n=3)
    sweep = pat.sweep_reclaim(df, ref)
    assert bool(sweep.iloc[3]) is True
    assert bool(sweep.iloc[4]) is False


def test_fvg_entry_event_fires_on_retrace_and_hold():
    """Gap [100,102] forms at t2; price retraces into it at t3 and closes above
    the gap bottom -> entry queued for t4's open."""
    df = _frame([
        [100, 100,  95,  98, 1000],
        [ 98, 110,  97, 108, 3000],
        [108, 115, 102, 112, 2000],
        [112, 113, 101, 105, 1500],   # retraces into the zone, holds
        [105, 108, 104, 107, 1200],
    ])
    events = pat.fvg_entry_events(df, retrace_window=5, atr_window=2, stop_buffer_atr=0.0)
    assert len(events) == 1
    ev = events[0]
    assert (ev.formation_idx, ev.trigger_idx, ev.entry_idx) == (2, 3, 4)
    assert ev.stop_level == pytest.approx(100.0)


def test_fvg_invalidated_gap_produces_no_event():
    """A close below the gap bottom kills the setup -- it does not wait for a
    later retrace."""
    df = _frame([
        [100, 100,  95,  98, 1000],
        [ 98, 110,  97, 108, 3000],
        [108, 115, 102, 112, 2000],
        [112, 113,  90,  95, 1500],   # closes below gap bottom -> invalidated
        [ 95, 105, 100, 104, 1200],
        [104, 108, 101, 107, 1200],
    ])
    assert pat.fvg_entry_events(df, retrace_window=5, atr_window=2) == []


def test_displacement_filter_can_be_disabled():
    """displacement_min=None must disable the filter entirely -- 'displacement
    contributes nothing' is a live hypothesis, not an assumption."""
    df = _frame([
        [100, 100,  95,  98, 1000],
        [ 98, 110,  97, 108, 3000],
        [108, 115, 102, 112, 2000],
        [112, 113, 101, 105, 1500],
        [105, 108, 104, 107, 1200],
    ])
    off = pat.fvg_entry_events(df, retrace_window=5, atr_window=2, displacement_min=None)
    strict = pat.fvg_entry_events(
        df, retrace_window=5, atr_window=2, displacement_min=99.0
    )
    assert len(off) == 1
    assert strict == [], "an impossible displacement threshold must reject everything"


def test_ifvg_requires_formation_inversion_and_retest():
    """Bearish gap [92,95] at t2; close above 95 at t3 inverts it; retest at t4
    holds -> entry at t5."""
    df = _frame([
        [100, 100, 95, 96, 1000],
        [ 96,  99, 88, 90, 3000],
        [ 90,  92, 85, 87, 2000],
        [ 87,  98, 86, 97, 2500],   # closes above 95 -> inverted
        [ 97,  99, 93, 96, 1800],   # retests zone, holds above 92
        [ 96, 100, 95, 99, 1500],
    ])
    events = pat.ifvg_entry_events(df, inversion_window=5, retrace_window=5, atr_window=2)
    assert len(events) == 1
    ev = events[0]
    assert ev.setup == "ifvg_reversal"
    assert (ev.formation_idx, ev.trigger_idx, ev.entry_idx) == (2, 4, 5)


def test_ifvg_without_inversion_produces_no_event():
    df = _frame([
        [100, 100, 95, 96, 1000],
        [ 96,  99, 88, 90, 3000],
        [ 90,  92, 85, 87, 2000],
        [ 87,  91, 86, 89, 2500],   # never closes above 95
        [ 89,  91, 87, 90, 1800],
        [ 90,  92, 88, 91, 1500],
    ])
    assert pat.ifvg_entry_events(df, inversion_window=5, retrace_window=5, atr_window=2) == []


def test_signal_events_never_enter_on_the_trigger_bar():
    """Execution is always the NEXT bar's open. Entering on the trigger bar's
    close would assume knowledge of that close while trading it."""
    df = _frame([
        [100, 100,  95,  98, 1000],
        [ 98, 110,  97, 108, 3000],
        [108, 115, 102, 112, 2000],
        [112, 113, 101, 105, 1500],
        [105, 108, 104, 107, 1200],
    ])
    for ev in pat.fvg_entry_events(df, retrace_window=5, atr_window=2):
        assert ev.entry_idx == ev.trigger_idx + 1
