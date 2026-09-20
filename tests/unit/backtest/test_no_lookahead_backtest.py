"""The property that matters most: the past must not depend on the future.

Every other test checks a rule. This one checks the thing that makes a backtest
worth reading at all -- that truncating the data at some date leaves every trade
that opened and closed before that date completely unchanged.

If any part of the pipeline peeks ahead (a centred window, a fill on the signal
bar, a ranking computed over the whole series), truncation moves those trades
and this test fails.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from screener.backtest.engine import CostModel, ExitRule, run_backtest
from screener.backtest.strategies import (
    TrendFilter,
    pattern_candidates,
    relative_strength_candidates,
)
from screener.calc.splits import Split, adjust_bars


def synthetic(seed: int, n: int = 700, start: str = "2015-01-01") -> pd.DataFrame:
    """A random walk with gaps and reversals, seeded for reproducibility."""
    rng = np.random.default_rng(seed)
    index = pd.bdate_range(start, periods=n)
    steps = rng.normal(0.0006, 0.018, n)
    close = 100.0 * np.exp(np.cumsum(steps))
    spread = np.abs(rng.normal(0.012, 0.006, n)) * close
    open_ = close * (1.0 + rng.normal(0.0, 0.006, n))
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.uniform(1e6, 5e6, n),
        },
        index=index,
    )


def universe(seeds=(1, 2, 3, 4)) -> dict[str, pd.DataFrame]:
    bars = {f"SYM{i}": synthetic(i) for i in seeds}
    bars["SPY"] = synthetic(99)
    return bars


def comparable(trades, cutoff: date):
    """Trades that both opened and closed strictly before the cutoff."""
    return {
        (t.ticker, t.entry_date, t.exit_date, str(t.entry_price), str(t.exit_price))
        for t in trades
        if t.exit_date is not None and t.exit_date < cutoff
    }


def truncate(bars: dict[str, pd.DataFrame], cutoff: date) -> dict[str, pd.DataFrame]:
    stamp = pd.Timestamp(cutoff)
    return {k: v.loc[v.index < stamp] for k, v in bars.items()}


def _run(bars, candidates, end):
    return run_backtest(
        candidates,
        bars,
        start=date(2015, 1, 1),
        end=end,
        exit_rule=ExitRule(r_multiple=2.0, time_limit=10),
        costs=CostModel(slippage_bps=5.0),
    )


def test_fvg_trades_are_unchanged_by_truncating_the_future():
    cutoff = date(2016, 6, 1)
    full = universe()

    all_trades = _run(
        full, pattern_candidates(full, hypothesis="h2"), date(2030, 1, 1)
    ).trades
    partial_bars = truncate(full, cutoff)
    partial_trades = _run(
        partial_bars, pattern_candidates(partial_bars, hypothesis="h2"), cutoff
    ).trades

    settled = comparable(all_trades, cutoff)
    assert settled, "no settled trades to compare -- the test would prove nothing"
    assert settled == comparable(partial_trades, cutoff)


def test_sweep_trades_are_unchanged_by_truncating_the_future():
    cutoff = date(2016, 6, 1)
    full = universe()

    all_trades = _run(
        full, pattern_candidates(full, hypothesis="h3"), date(2030, 1, 1)
    ).trades
    partial_bars = truncate(full, cutoff)
    partial_trades = _run(
        partial_bars, pattern_candidates(partial_bars, hypothesis="h3"), cutoff
    ).trades

    settled = comparable(all_trades, cutoff)
    assert settled
    assert settled == comparable(partial_trades, cutoff)


def test_relative_strength_ranking_is_unchanged_by_truncating_the_future():
    """Cross-sectional ranking is the easiest place to leak the future: rank
    over the whole series instead of per-date and every past trade shifts."""
    cutoff = date(2016, 6, 1)
    full = universe()

    all_trades = _run(
        full,
        relative_strength_candidates(full, trend=TrendFilter(enabled=False), top_pct=0.5),
        date(2030, 1, 1),
    ).trades
    partial_bars = truncate(full, cutoff)
    partial_trades = _run(
        partial_bars,
        relative_strength_candidates(
            partial_bars, trend=TrendFilter(enabled=False), top_pct=0.5
        ),
        cutoff,
    ).trades

    settled = comparable(all_trades, cutoff)
    assert settled
    assert settled == comparable(partial_trades, cutoff)


def test_backtest_is_deterministic():
    full = universe()
    candidates = pattern_candidates(full, hypothesis="h2")
    first = _run(full, candidates, date(2030, 1, 1))
    second = _run(full, candidates, date(2030, 1, 1))
    assert [t.__dict__ for t in first.trades] == [t.__dict__ for t in second.trades]


def test_a_delayed_and_rechecked_entry_is_unchanged_by_truncating_the_future():
    """The re-check re-ranks on a later day. It must use that day's close and
    nothing after it, or truncation moves trades that had already settled."""
    cutoff = date(2016, 6, 1)
    full = universe()
    kw = dict(trend=TrendFilter(), top_pct=0.5, entry_delay=6, rebalance_days=5)

    all_trades = _run(full, relative_strength_candidates(full, **kw), date(2030, 1, 1)).trades
    partial_bars = truncate(full, cutoff)
    partial_trades = _run(
        partial_bars, relative_strength_candidates(partial_bars, **kw), cutoff
    ).trades

    settled = comparable(all_trades, cutoff)
    assert settled
    assert settled == comparable(partial_trades, cutoff)


# --- split adjustment, added 2026-09-20 -------------------------------------
#
# Back-adjustment scales PAST prices by FUTURE splits, which is the shape of a
# lookahead violation. It is safe only because a split outside the window
# multiplies every bar in the window by the same constant, and every quantity
# the engine decides on is a ratio. These pin that, because the reasoning is
# not obvious and the existing tests above contain no splits at all.


def test_a_split_after_the_window_changes_trades_if_it_is_applied():
    """Why `splits_until` exists, pinned as the failure it prevents.

    Back-adjustment scales PAST prices by FUTURE splits. For returns that is
    harmless: a split outside the window multiplies every bar in it by one
    constant, which cancels in every ratio. For SHARE COUNTS it is not. A
    1-for-50 reverse split lifts a $20 bar to $1,018, and at $10,000 of equity
    the risk budget then buys no whole shares at all.

    Measured when this was written: 68 settled trades became zero.
    """
    cutoff = date(2016, 6, 1)
    full = universe()
    lifted = {k: adjust_bars(v, [Split(date(2020, 1, 2), 0.02)]) for k, v in full.items()}

    def settled(bars):
        trades = _run(
            bars,
            relative_strength_candidates(bars, trend=TrendFilter(enabled=False), top_pct=0.5),
            date(2030, 1, 1),
        ).trades
        return [t for t in trades if t.exit_date is not None and t.exit_date < cutoff]

    assert settled(full), "the unscaled run should produce trades to lose"
    assert not settled(lifted), (
        "if this ever passes, the engine stopped sizing off absolute prices "
        "and `splits_until` may no longer be load-bearing"
    )


def test_a_split_inside_the_window_is_what_the_adjustment_is_for():
    """The counterpart. A split the window CONTAINS must change the series,
    because leaving it raw is the defect: a 1-for-50 reverse split reads as a
    +4,900% one-day return and the name tops every momentum ranking."""
    full = universe()
    inside = {k: adjust_bars(v, [Split(date(2016, 1, 4), 0.02)]) for k, v in full.items()}

    before = full["SYM1"]["close"]
    after = inside["SYM1"]["close"]
    early = pd.Timestamp("2015-06-01")

    assert after.loc[early] == pytest.approx(before.loc[early] * 50)
    assert after.iloc[-1] == pytest.approx(before.iloc[-1])
