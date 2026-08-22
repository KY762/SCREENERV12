"""Momentum with a skip period, hand-computed.

The skip is the part most easily got wrong, and getting it wrong is silent:
the series still looks like momentum, it just quietly mixes in the reversal
signal the skip exists to exclude.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from screener.calc.momentum import (
    momentum_skip,
    month_end_mask,
    relative_momentum_skip,
    volatility_scaled_momentum,
)


def ramp(values: list[float], start: str = "2024-01-01") -> pd.Series:
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype="float64")


def test_momentum_skip_measures_between_the_two_shifted_points():
    """With lookback 4 and skip 2, the bar at index 4 compares close[2] against
    close[0]: (120 - 100) / 100 = 0.20. The last two bars are excluded."""
    close = ramp([100, 110, 120, 200, 300])

    out = momentum_skip(close, lookback=4, skip=2)

    assert out.iloc[4] == pytest.approx(0.20)


def test_the_skipped_window_is_genuinely_excluded():
    """Changing only the most recent bars must not move a 12-1 style reading."""
    base = ramp([100, 105, 110, 115, 120, 125, 130])
    spiked = base.copy()
    spiked.iloc[-1] = 400.0

    a = momentum_skip(base, lookback=5, skip=2)
    b = momentum_skip(spiked, lookback=5, skip=2)

    assert a.iloc[-1] == pytest.approx(b.iloc[-1])


def test_skip_zero_is_an_ordinary_trailing_return():
    close = ramp([100, 110, 120, 130])
    assert momentum_skip(close, lookback=3, skip=0).iloc[3] == pytest.approx(0.30)


def test_warmup_is_null_rather_than_fabricated():
    close = ramp([100, 110, 120, 130])
    out = momentum_skip(close, lookback=3, skip=1)
    assert out.iloc[:3].isna().all()


def test_lookback_must_exceed_skip():
    with pytest.raises(ValueError, match="must exceed"):
        momentum_skip(ramp([1.0, 2.0, 3.0]), lookback=2, skip=2)


def test_relative_momentum_is_the_difference_of_two_skips():
    symbol = ramp([100, 100, 100, 150, 150])
    bench = ramp([100, 100, 100, 120, 120])

    out = relative_momentum_skip(symbol, bench, lookback=3, skip=1)

    # symbol +50%, benchmark +20%, over the same window
    assert out.iloc[4] == pytest.approx(0.30)


def test_volatility_scaling_penalises_the_noisier_path():
    """Two names with the same total move; the one that got there erratically
    ranks lower. Without this, a momentum ranking is partly a volatility bet."""
    rng = np.random.default_rng(4)
    n = 300
    index = pd.bdate_range("2023-01-01", periods=n)
    drift = np.linspace(0, 0.4, n)
    calm = pd.Series(100 * np.exp(drift + rng.normal(0, 0.002, n)), index=index)
    wild = pd.Series(100 * np.exp(drift + rng.normal(0, 0.030, n)), index=index)

    calm_score = volatility_scaled_momentum(calm, 252, 21).iloc[-1]
    wild_score = volatility_scaled_momentum(wild, 252, 21).iloc[-1]

    assert calm_score > wild_score


def test_month_end_mask_marks_the_last_trading_day_of_each_month():
    index = pd.bdate_range("2024-01-01", "2024-03-31")
    mask = month_end_mask(index)

    marked = index[mask.to_numpy()]
    assert len(marked) == 3
    assert str(marked[0].date()) == "2024-01-31"
    assert str(marked[1].date()) == "2024-02-29"      # leap year
    assert str(marked[2].date()) == "2024-03-29"      # last business day


def test_month_end_mask_marks_the_final_bar_even_mid_month():
    """Rebalancing must still happen on the last bar available, or the final
    period is silently dropped."""
    index = pd.bdate_range("2024-01-01", "2024-02-14")
    assert bool(month_end_mask(index).iloc[-1])
