"""Range compression, expansion, and effort-vs-result.

Built on constructed series where the answer is known by inspection, because
'the volatility got quieter' is exactly the kind of claim that looks right on a
chart and is wrong in the code.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from screener.calc.compression import (
    atr_ratio,
    effort_vs_result,
    expansion_events,
    is_compressed,
    range_percentile,
)


def series(spans: list[float], base: float = 100.0, volume: float = 1_000_000.0):
    """A frame whose daily range is exactly ``spans[i]``, price flat at base."""
    index = pd.bdate_range("2023-01-01", periods=len(spans))
    return pd.DataFrame(
        {
            "open": base,
            "high": [base + s / 2 for s in spans],
            "low": [base - s / 2 for s in spans],
            "close": base,
            "volume": volume,
        },
        index=index,
    )


def test_atr_ratio_falls_when_recent_range_narrows():
    wide = [4.0] * 60
    narrow = [1.0] * 30
    df = series(wide + narrow)

    out = atr_ratio(df, fast=14, slow=50)

    assert out.iloc[-1] < 0.6, "a quarter-width recent range must pull the ratio well below 1"


def test_atr_ratio_is_about_one_when_nothing_changes():
    df = series([2.0] * 120)
    assert atr_ratio(df, 14, 50).iloc[-1] == pytest.approx(1.0, abs=0.05)


def test_range_percentile_puts_the_quietest_stretch_near_zero():
    df = series([5.0] * 100 + [0.5] * 20)
    out = range_percentile(df, window=60, atr_window=14)
    assert out.iloc[-1] < 0.2


def test_range_percentile_puts_the_noisiest_stretch_near_one():
    df = series([1.0] * 100 + [9.0] * 20)
    out = range_percentile(df, window=60, atr_window=14)
    assert out.iloc[-1] > 0.8


def test_compression_flag_follows_the_percentile():
    df = series([5.0] * 100 + [0.5] * 20)
    flags = is_compressed(df, percentile=0.20, window=60)
    assert bool(flags.iloc[-1])
    assert not bool(flags.iloc[80])


def test_warmup_is_null_not_zero():
    """A percentile computed on partial history is not a percentile."""
    df = series([2.0] * 40)
    assert range_percentile(df, window=126).isna().all()


def test_an_expansion_after_a_quiet_stretch_is_detected():
    """Quiet range, then a close above the prior 20-bar high."""
    n = 160
    index = pd.bdate_range("2023-01-01", periods=n)
    high = np.full(n, 100.5)
    low = np.full(n, 99.5)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    # A noisy first stretch so the quiet stretch ranks low in its own history.
    high[:60] += 4.0
    low[:60] -= 4.0
    # The break.
    high[-2] = 108.0
    close[-2] = 107.0
    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": 1e6},
        index=index,
    )

    events = expansion_events(df, percentile=0.35, window=120, breakout_window=20)

    assert len(events) == 1
    assert events[0].setup == "range_expansion"
    assert events[0].entry_idx == events[0].trigger_idx + 1, "execution is the NEXT bar"
    assert events[0].stop_level < 99.5, "the stop sits below the compressed range"


def test_no_expansion_without_a_preceding_compression():
    """A breakout on its own is a different setup. This one requires the quiet
    period first, or it is just a 20-day high."""
    n = 160
    index = pd.bdate_range("2023-01-01", periods=n)
    rng = np.random.default_rng(7)
    span = rng.uniform(3.0, 5.0, n)          # never quiet
    close = np.full(n, 100.0)
    close[-2] = 130.0
    df = pd.DataFrame(
        {
            "open": 100.0, "high": 100 + span / 2, "low": 100 - span / 2,
            "close": close, "volume": 1e6,
        },
        index=index,
    )
    df.loc[df.index[-2], "high"] = 131.0

    assert expansion_events(df, percentile=0.10, window=120) == []


def test_one_entry_per_compression_episode():
    """Without the re-arm rule, a single quiet stretch fires on every later bar
    that happens to close above the old high -- one setup counted thirty times.

    The quiet stretch must run past the percentile warmup before the rally
    starts, or nothing is ever armed and the test proves nothing.
    """
    n = 220
    index = pd.bdate_range("2023-01-01", periods=n)
    high = np.full(n, 100.5)
    low = np.full(n, 99.5)
    close = np.full(n, 100.0)
    high[:60] += 4.0
    low[:60] -= 4.0
    for i in range(170, 200):                 # a sustained march upward
        close[i] = 101.0 + (i - 170)
        high[i] = close[i] + 0.5
    df = pd.DataFrame(
        {"open": 100.0, "high": high, "low": low, "close": close, "volume": 1e6},
        index=index,
    )

    events = expansion_events(df, percentile=0.35, window=120, breakout_window=20)

    assert len(events) == 1, "thirty rising bars are one episode, not thirty setups"


def test_effort_vs_result_is_low_when_volume_is_heavy_and_range_narrow():
    """Absorption: someone is filling size against the move."""
    quiet_heavy = series([1.0] * 60, volume=5_000_000.0)
    normal = series([1.0] * 60, volume=1_000_000.0)

    absorbed = effort_vs_result(quiet_heavy).iloc[-1]
    ordinary = effort_vs_result(normal).iloc[-1]

    assert absorbed == pytest.approx(ordinary), (
        "with volume flat at its own average, the ratio depends only on range"
    )


def test_effort_vs_result_rises_when_price_travels_on_light_volume():
    n = 60
    df = series([1.0] * n)
    df.iloc[-1, df.columns.get_loc("high")] = 106.0
    df.iloc[-1, df.columns.get_loc("low")] = 94.0        # wide range
    df.iloc[-1, df.columns.get_loc("volume")] = 200_000.0  # light volume

    out = effort_vs_result(df)

    assert out.iloc[-1] > out.iloc[-2] * 5
