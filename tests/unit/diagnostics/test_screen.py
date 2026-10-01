"""H8, the avoid screen (docs/11): trades follow the engine's rules, the screen
drops the pool's top fifth, and the diagnostic refuses budgeted splits."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from screener.backtest.splits import get_split
from screener.diagnostics.screen import judge, measure, trade_return


def _bars(closes, volumes=None, start="2010-01-04"):
    closes = np.asarray(closes, dtype="float64")
    idx = pd.bdate_range(start, periods=len(closes))
    vol = np.full(len(closes), 1e6) if volumes is None else np.asarray(volumes, dtype="float64")
    return pd.DataFrame({"open": closes, "high": closes, "low": closes,
                         "close": closes, "volume": vol}, index=idx)


def test_trade_fills_next_open_and_exits_after_the_horizon():
    bars = _bars(np.arange(1, 50, dtype=float))
    assert trade_return(bars, 10, 5) == pytest.approx(17.0 / 12.0 - 1.0)


def test_trade_is_refused_on_a_zero_volume_entry_bar():
    vol = np.full(50, 1e6)
    vol[11] = 0
    assert trade_return(_bars(np.full(50, 10.0), vol), 10, 5) is None


def test_trade_exits_at_the_open_of_a_zero_volume_bar():
    closes = np.full(50, 10.0)
    closes[13] = 12.0
    vol = np.full(50, 1e6)
    vol[13] = 0
    assert trade_return(_bars(closes, vol), 10, 5) == pytest.approx(0.2)


def test_trade_exits_at_the_last_close_when_the_series_ends():
    closes = np.full(15, 10.0)
    closes[-1] = 8.0
    assert trade_return(_bars(closes), 10, 20) == pytest.approx(-0.2)


def test_budgeted_splits_are_refused():
    with pytest.raises(ValueError, match="development"):
        measure({}, split=get_split("validation"), eligible=lambda t, d: True, spreads={})


def test_budget_cleared_allows_a_budgeted_split_to_run():
    """The CLI sets this only after `budget.check` has authorized the run.
    Calling `measure` directly still refuses by default (the test above)."""
    rng = np.random.default_rng(1)
    bars = {}
    for k in range(60):
        r = rng.normal(0.0005, 0.015, 400)
        bars[f"S{k}"] = _bars(20 * np.cumprod(1 + r), start="2016-01-04")
    windows = measure(bars, split=get_split("validation"), eligible=lambda t, d: True,
                      spreads={}, horizon=20, stride=20, budget_cleared=True)
    assert windows, "budget_cleared=True must let a non-development split actually run"


def _pool(n_calm, n_wild, seed=0):
    """Calm names drift up; wild names are volatile and drift down."""
    rng = np.random.default_rng(seed)
    bars = {}
    for k in range(n_calm):
        r = rng.normal(0.0008, 0.01, 400)
        bars[f"C{k}"] = _bars(20 * np.cumprod(1 + r))
    for k in range(n_wild):
        r = rng.normal(-0.0015, 0.06, 400)
        bars[f"W{k}"] = _bars(20 * np.cumprod(1 + r))
    return bars


def test_screen_leaves_out_the_volatile_fifth_and_measures_the_gain():
    bars = _pool(80, 20)
    windows = measure(bars, split=get_split("development"),
                      eligible=lambda t, d: True, spreads={}, horizon=20, stride=20)
    assert windows
    assert all(0.19 <= w.share_out <= 0.40 for w in windows)
    verdict = judge(windows, get_split("development"))
    assert verdict.mean_gross > 0          # removing the losing wild names helps


def test_eligibility_is_respected():
    bars = _pool(80, 20)
    only_calm = measure(bars, split=get_split("development"),
                        eligible=lambda t, d: t.startswith("C"), spreads={})
    assert only_calm
    assert all(w.names <= 80 for w in only_calm)
    assert date(2010, 1, 1) <= only_calm[0].day
