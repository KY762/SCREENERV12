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

from screener.backtest.engine import CostModel, ExitRule, run_backtest
from screener.backtest.strategies import (
    TrendFilter,
    pattern_candidates,
    relative_strength_candidates,
)


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
