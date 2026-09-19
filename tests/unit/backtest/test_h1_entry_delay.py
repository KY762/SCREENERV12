"""H1's entry delay, and the re-check the operator chose for it (2026-09-18).

With a delay of d sessions, a name ranked on day s is bought at the open d
sessions later -- but only if, at the last close before that open, it STILL
ranks in the top slice and still passes the trend filter. These tests pin both
halves, using the function itself as the oracle: run with a one-session delay
and a daily rebalance, it lists exactly who is in the slice on every day.
"""

from __future__ import annotations

import pytest

from screener.backtest.strategies import TrendFilter, relative_strength_candidates
from tests.unit.backtest.test_no_lookahead_backtest import universe

KW = dict(trend=TrendFilter(), top_pct=0.5, lookback=20)


def slice_membership(bars) -> set[tuple[str, object]]:
    """(ticker, day) for every day the name ranked in the top slice."""
    daily = relative_strength_candidates(bars, rebalance_days=1, **KW)
    return {(c.ticker, c.signal_date) for c in daily}


def test_a_one_session_delay_is_the_original_rule():
    bars = universe()
    assert relative_strength_candidates(bars, rebalance_days=5, **KW) == \
        relative_strength_candidates(bars, rebalance_days=5, entry_delay=1, **KW)


@pytest.mark.parametrize("delay", [3, 6])
def test_a_delayed_name_is_kept_exactly_when_it_still_ranks_at_the_last_close(delay):
    bars = universe()
    in_slice = slice_membership(bars)
    ranked = relative_strength_candidates(bars, rebalance_days=5, **KW)

    expected = {}
    for c in ranked:
        index = bars[c.ticker].index
        p = index.get_indexer([c.signal_date])[0]
        if p + delay >= len(index):
            continue
        check_day = index[p + delay - 1].date()
        if (c.ticker, check_day) in in_slice:
            expected[(c.ticker, c.signal_date)] = index[p + delay].date()

    delayed = relative_strength_candidates(bars, rebalance_days=5, entry_delay=delay, **KW)
    got = {(c.ticker, c.signal_date): c.entry_date for c in delayed}

    assert got == expected
    assert len(got) < len(ranked), "the re-check should drop someone on this data"


def test_the_delay_waits_the_stated_number_of_sessions():
    bars = universe()
    for c in relative_strength_candidates(bars, rebalance_days=5, entry_delay=3, **KW):
        index = bars[c.ticker].index
        gap = index.get_indexer([c.entry_date])[0] - index.get_indexer([c.signal_date])[0]
        assert gap == 3


def test_a_delay_below_one_is_refused():
    """0 would buy at the ranking bar's own open, before the close that
    completes the signal -- the lookahead non-negotiable #1 forbids."""
    with pytest.raises(ValueError, match="entry_delay"):
        relative_strength_candidates(universe(), entry_delay=0, **KW)
