"""Impossible bars: each kind handled the way calc/validity.py says, and real
moves left exactly as they were."""

import numpy as np
import pandas as pd

from screener.calc.validity import clean_pieces, repair


def _frame(closes, volumes=None, start="2012-01-02"):
    closes = np.asarray(closes, dtype="float64")
    idx = pd.bdate_range(start, periods=len(closes))
    if volumes is None:
        vol = np.full(len(closes), 1_000_000.0)
    else:
        vol = np.asarray(volumes, dtype="float64")
    return pd.DataFrame(
        {"open": closes, "high": closes * 1.01, "low": closes * 0.99,
         "close": closes, "volume": vol},
        index=idx,
    )


def _returns_across(pieces):
    """Every one-bar close-to-close ratio inside the pieces -- what any
    indicator or trade could read."""
    out = []
    for p in pieces:
        c = p["close"].to_numpy()
        out.extend(c[1:] / c[:-1])
    return np.asarray(out)


def test_clean_series_comes_back_untouched():
    frame = _frame(20 + np.sin(np.arange(300) / 10))
    fixed, report = repair(frame)
    assert not report.touched
    pd.testing.assert_frame_equal(fixed, frame)


def test_zero_volume_bar_priced_away_takes_the_last_traded_close():
    closes = [28.0] * 30
    volumes = [1e6] * 30
    closes[10], volumes[10] = 1125.51, 0.0        # the NLCS shape
    fixed, report = repair(_frame(closes, volumes))
    assert len(report.repriced) == 1
    assert fixed["open"].iloc[10] == 28.0 and fixed["close"].iloc[10] == 28.0
    assert fixed["volume"].iloc[10] == 0.0        # still a zero-volume bar: no_volume exit sees it


def test_zero_volume_bar_near_the_last_price_is_left_alone():
    closes = [28.0] * 30
    volumes = [1e6] * 30
    closes[10], volumes[10] = 28.5, 0.0
    _, report = repair(_frame(closes, volumes))
    assert not report.repriced


def test_a_spike_that_reverts_is_dropped():
    closes = [20.0] * 40
    closes[15:17] = [2000.0, 2010.0]              # x100 for two days, then back
    fixed, report = repair(_frame(closes))
    assert len(report.dropped) == 2
    assert fixed["close"].max() == 20.0


def test_a_hundredfold_level_shift_cuts_the_series():
    closes = [11.0] * 60 + [1100.0] * 60          # the SCU shape
    volumes = [1e6] * 60 + [1e4] * 60
    pieces, report = clean_pieces(_frame(closes, volumes))
    assert len(report.cuts) == 1
    assert len(pieces) == 2
    assert _returns_across(pieces).max() < 1.1    # no return spans the join


def test_a_real_crash_is_kept():
    """Clovis, 2015-11-16: -70% in a day on heavy volume. Cutting it would let a
    position leave at the prior close, so it must stay."""
    closes = [100.0] * 60 + [30.0] * 60
    volumes = [1e6] * 60 + [5e6] * 60
    pieces, report = clean_pieces(_frame(closes, volumes))
    assert not report.cuts
    assert len(pieces) == 1
    assert report.kept                            # recorded as impossible-looking, left alone
    assert _returns_across(pieces).min() < 0.31


def test_a_real_surge_on_heavy_volume_is_kept():
    """Intercept, 2014-01-09: x3.8 in a day, volume up."""
    closes = [70.0] * 60 + [266.0] * 60
    volumes = [1e6] * 60 + [4e6] * 60
    pieces, report = clean_pieces(_frame(closes, volumes))
    assert not report.cuts and len(pieces) == 1


def test_a_rise_on_collapsing_share_volume_is_a_reverse_split():
    closes = [4.0] * 60 + [16.0] * 60              # x4, volume /4: unrecorded 1-for-4
    volumes = [4e6] * 60 + [1e6] * 60
    _, report = clean_pieces(_frame(closes, volumes))
    assert len(report.cuts) == 1


def test_a_fall_below_a_tenth_is_always_cut():
    closes = [50.0] * 60 + [0.2] * 60
    _, report = clean_pieces(_frame(closes))
    assert len(report.cuts) == 1


def test_an_excursion_and_its_return_a_year_later_are_both_cut():
    """The mid-December pattern: x10 one year, /10 the next."""
    closes = [5.0] * 60 + [50.0] * 250 + [5.0] * 60
    pieces, report = clean_pieces(_frame(closes))
    assert len(report.cuts) == 2
    assert len(pieces) == 3


def test_a_hole_is_cut_before_anything_is_compared_across_it():
    first = _frame([30.0] * 60, start="2010-01-04")
    second = _frame([300.0] * 60, start="2012-01-02")   # another security after the hole
    pieces, report = clean_pieces(pd.concat([first, second]))
    assert len(pieces) == 2
    assert not report.cuts             # the gap rule, not this module, made the cut
