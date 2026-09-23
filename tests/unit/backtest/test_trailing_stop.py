"""The trailing stop: the mechanism the convex strategy lives on.

Selection in small caps was measured on 2026-09-22 to pick VOLATILITY
symmetrically. The top momentum decile's best 1% runs to +34.9% against the
universe's +25.5%, and its worst 1% to -31.4% against -22.6%, with a median
edge of +0.05% per 20 days -- less than the spread costs to trade. Selection
alone therefore loses money.

So the asymmetry has to be manufactured: cut the left tail, leave the right one
alone. These tests pin that it does, and that it does not cheat to do so.
"""

from __future__ import annotations

from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from screener.backtest.engine import Candidate, CostModel, ExitRule, run_backtest


def series(closes, highs=None, lows=None, start="2015-01-02"):
    n = len(closes)
    c = np.asarray(closes, dtype="float64")
    return pd.DataFrame(
        {
            "open": c,
            "high": c if highs is None else np.asarray(highs, dtype="float64"),
            "low": c if lows is None else np.asarray(lows, dtype="float64"),
            "close": c,
            "volume": np.full(n, 1e6),
        },
        index=pd.bdate_range(start, periods=n),
    )


def candidate(bars, atr=1.0):
    return Candidate(
        ticker="AAA", setup="test",
        signal_date=bars.index[0].date(),
        entry_date=bars.index[1].date(),
        stop_distance=3.0 * atr, atr=atr, rank=1.0,
    )


def run(bars, rule, equity=100_000):
    return run_backtest(
        [candidate(bars)], {"AAA": bars},
        start=bars.index[0].date(), end=bars.index[-1].date(),
        starting_equity=equity, exit_rule=rule,
        costs=CostModel(slippage_bps=0.0),
    )


def test_the_stop_ratchets_up_and_never_down():
    """A rise then a pullback. With a fixed stop the trade survives the dip; a
    trailing stop has moved up behind the rise and takes the winner out."""
    bars = series([100, 100, 110, 120, 130, 126, 100, 100])

    fixed = run(bars, ExitRule(r_multiple=None, time_limit=None, use_stop=True))
    trailed = run(bars, ExitRule(r_multiple=None, time_limit=None,
                                 use_stop=True, trail_atr=3.0))

    (ft,) = fixed.trades
    (tt,) = trailed.trades
    assert tt.exit_date is not None
    assert tt.stop > ft.stop, "the trail should have raised the stop"
    assert tt.exit_price > ft.entry_price, "and banked a winner rather than a loss"


def test_a_winner_is_not_truncated_while_it_keeps_running():
    """The right tail is the entire point. A position that only rises must stay
    open -- a trail that exits on strength would cap exactly the moves the
    strategy depends on."""
    bars = series([100, 100, 110, 125, 140, 160, 185, 210])

    result = run(bars, ExitRule(r_multiple=None, time_limit=None,
                                use_stop=True, trail_atr=3.0))

    (trade,) = result.trades
    assert trade.exit_date is None, "still rising, so still open"


def test_the_ratchet_reads_only_closes_the_position_already_lived_through():
    """The lookahead trap inside a single bar.

    Raising the stop on TODAY's close and then testing today's low against it
    exits on a level the price was never subject to. It would never show up as
    a truncation failure, because truncating the data leaves those bars intact.

    Here the close rises far enough that a same-bar ratchet would lift the stop
    above the same bar's low and exit; a correct ratchet uses yesterday's close
    and leaves the position open.
    """
    # Entry at 100, ATR 1, so the stop starts at 97. Day four travels from a
    # low of 110 to a close of 130. A same-bar ratchet would lift the stop to
    # 127 and exit against that same bar's low of 110 -- a level the position
    # was never subject to. The low stays clear of the ORIGINAL stop, so
    # anything that exits here exited on a stop it invented mid-bar.
    bars = series(
        closes=[100, 100, 100, 130, 132],
        highs=[100, 100, 101, 131, 133],
        lows=[100, 100, 99, 110, 131],
    )

    result = run(bars, ExitRule(r_multiple=None, time_limit=None,
                                use_stop=True, trail_atr=3.0))

    (trade,) = result.trades
    assert trade.exit_date is None, (
        "a same-bar ratchet would have exited on a low the stop never covered"
    )


def test_no_trail_leaves_the_stop_exactly_where_it_started():
    """`trail_atr=None` must be inert -- every result before 2026-09-22 was
    measured with a fixed stop and has to stay reproducible."""
    bars = series([100, 100, 130, 160, 120])

    result = run(bars, ExitRule(r_multiple=None, time_limit=None, use_stop=True))

    (trade,) = result.trades
    assert trade.stop == pytest.approx(Decimal(str(trade.entry_price)) - Decimal("3"))


def test_a_gap_through_the_trailed_stop_fills_at_the_open():
    """Ambiguity resolves against us (non-negotiable 6). Selecting volatile
    names maximises gap risk, so this is the case that decides whether the left
    tail is really cut at -1R."""
    bars = series([100, 100, 140, 141, 90, 90])

    result = run(bars, ExitRule(r_multiple=None, time_limit=None,
                                use_stop=True, trail_atr=3.0))

    (trade,) = result.trades
    assert trade.exit_reason == "stop_gap"
    assert trade.exit_price == pytest.approx(Decimal("90"))
    assert trade.exit_price < trade.stop, "gapped below the stop, no protection"


def test_a_zero_time_limit_means_no_time_exit():
    """Zero means NO time exit, exactly as it does for a target.

    The engine tested `held >= time_limit`, so zero closed every position the
    bar after entry. Found on the first run of this strategy: 687 trades, all
    exiting on time, and a trailing stop that never fired once. Same shape as
    the r_multiple=0 bug that voided eight battery experiments.
    """
    bars = series([100, 100, 110, 120, 130, 140])

    result = run(bars, ExitRule(r_multiple=0, time_limit=0,
                                use_stop=True, trail_atr=3.0))

    (trade,) = result.trades
    assert trade.exit_reason != "time", "zero is not a one-bar hold"
    assert trade.exit_date is None, "still rising with no time limit, so still open"


def test_a_rule_with_no_exit_at_all_is_still_refused():
    """The guard has to survive the fix: no stop, no target, and a zero time
    limit is a rule that never closes a position."""
    with pytest.raises(ValueError, match="never exits"):
        ExitRule(r_multiple=0, time_limit=0, use_stop=False)
