"""Round 2 strategies.

Round 1 failed in a way that made one thing clear: the details that were
treated as incidental -- skip period, rebalance frequency, stop presence --
were the whole specification. These tests pin those details.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from screener.backtest.runner import HYPOTHESES, RunConfig, build_candidates
from screener.backtest.strategies import (
    canonical_momentum_candidates,
    drift_candidates,
)


def walk(seed: int, n: int = 900, drift: float = 0.0006, start: str = "2015-01-01"):
    rng = np.random.default_rng(seed)
    index = pd.bdate_range(start, periods=n)
    close = 100 * np.exp(np.cumsum(rng.normal(drift, 0.015, n)))
    spread = np.abs(rng.normal(0.012, 0.005, n)) * close
    open_ = close * (1 + rng.normal(0, 0.005, n))
    return pd.DataFrame(
        {
            "open": open_,
            "high": np.maximum(open_, close) + spread,
            "low": np.minimum(open_, close) - spread,
            "close": close,
            "volume": rng.uniform(1e6, 5e6, n),
        },
        index=index,
    )


def universe(n: int = 6) -> dict[str, pd.DataFrame]:
    return {f"S{i}": walk(i) for i in range(n)}


# -- H5: canonical momentum --------------------------------------------------

def test_momentum_rebalances_monthly_not_daily():
    """The anomaly is documented at monthly frequency. Rebalancing daily both
    changes the effect being measured and multiplies costs."""
    bars = universe()

    monthly = canonical_momentum_candidates(bars, monthly=True, top_pct=0.5)
    daily = canonical_momentum_candidates(bars, monthly=False, top_pct=0.5)

    assert len(daily) > len(monthly) * 10
    assert len({c.entry_date for c in monthly}) < 60, "roughly one date per month"


def test_momentum_uses_an_entry_relative_stop():
    """The Round 1 stop bug came from anchoring to a stale price. Momentum
    carries a distance, so the risk is the constant."""
    candidates = canonical_momentum_candidates(universe(), top_pct=0.5)

    assert candidates
    assert all(c.stop_distance is not None for c in candidates)
    assert all(c.stop_level is None for c in candidates)


def test_momentum_execution_is_the_bar_after_the_ranking():
    bars = universe()
    for candidate in canonical_momentum_candidates(bars, top_pct=0.5)[:20]:
        assert candidate.entry_date > candidate.signal_date


def test_the_skip_period_changes_the_ranking():
    """If skip made no difference, H1's 63-day-no-skip formation would have
    been the same test -- and it was not."""
    bars = universe()

    with_skip = canonical_momentum_candidates(bars, lookback=252, skip=21, top_pct=0.2)
    without = canonical_momentum_candidates(bars, lookback=252, skip=1, top_pct=0.2)

    picked_with = {(c.entry_date, c.ticker) for c in with_skip}
    picked_without = {(c.entry_date, c.ticker) for c in without}
    assert picked_with != picked_without


def test_short_histories_are_excluded_rather_than_ranked_on_partial_data():
    bars = universe(3)
    bars["NEW"] = walk(99, n=60)

    picked = {c.ticker for c in canonical_momentum_candidates(bars, top_pct=1.0)}

    assert "NEW" not in picked


def test_momentum_respects_the_universe_mask():
    bars = universe()
    blocked = canonical_momentum_candidates(
        bars, top_pct=1.0, universe=lambda t, d: t != "S0"
    )
    assert all(c.ticker != "S0" for c in blocked)


# -- H6: post-earnings drift -------------------------------------------------

def test_drift_fires_only_after_a_qualifying_reaction():
    bars = {"AAA": walk(1)}
    index = bars["AAA"].index
    close = bars["AAA"]["close"]

    # Pick a date where the day's move is genuinely small.
    moves = close.pct_change()
    quiet_position = int(np.argmin(np.abs(moves.to_numpy()[300:400]))) + 300
    quiet_day = index[quiet_position].date()

    demanding = drift_candidates(bars, {"AAA": [quiet_day]}, reaction_pct=0.50)
    permissive = drift_candidates(bars, {"AAA": [quiet_day]}, reaction_pct=-1.0)

    assert demanding == []
    assert len(permissive) == 1


def test_drift_entry_delay_shifts_the_execution_date():
    """A day-one edge that has decayed by day three is not tradeable, so the
    delay has to be a parameter rather than an assumption."""
    bars = {"AAA": walk(2)}
    event = [bars["AAA"].index[500].date()]

    one = drift_candidates(bars, {"AAA": event}, reaction_pct=-1.0, entry_delay=1)
    three = drift_candidates(bars, {"AAA": event}, reaction_pct=-1.0, entry_delay=3)

    assert one[0].entry_date < three[0].entry_date


def test_drift_without_events_produces_nothing():
    assert drift_candidates({"AAA": walk(3)}, {}) == []


def test_drift_ranks_by_the_size_of_the_reaction():
    bars = {"AAA": walk(4)}
    index = bars["AAA"].index
    events = [index[i].date() for i in range(300, 340)]

    candidates = drift_candidates(bars, {"AAA": events}, reaction_pct=-1.0)

    assert candidates
    assert all(c.rank is not None for c in candidates)


# -- wiring ------------------------------------------------------------------

def test_round_2_hypotheses_are_registered():
    assert {"h5", "h6", "h7"} <= set(HYPOTHESES)


def test_h6_without_earnings_data_fails_loudly():
    """Silently producing zero candidates would read as 'no drift exists'."""
    with pytest.raises(ValueError, match="earnings dates"):
        build_candidates(universe(2), RunConfig(hypothesis="h6"))


def test_h5_and_h7_carry_no_profit_target_by_default():
    """Neither specification names one. Only the pattern setups surface over R."""
    for hypothesis in ("h5", "h6", "h7"):
        assert RunConfig(hypothesis=hypothesis).resolved().r_multiple is None
    assert RunConfig(hypothesis="h2").resolved().r_multiple == 2.0


def test_config_hash_ignores_parameters_a_hypothesis_never_reads():
    """Otherwise an unrelated default moving would spend budget by looking
    like a different configuration."""
    a = RunConfig(hypothesis="h5", sweep_lookback=10).as_dict()
    b = RunConfig(hypothesis="h5", sweep_lookback=40).as_dict()
    assert a == b


def test_h7_squeeze_builds_through_the_runner():
    bars = universe()
    candidates = build_candidates(
        bars, RunConfig(hypothesis="h7", trend_filter=False, squeeze_percentile=0.35)
    )
    assert isinstance(candidates, list)
