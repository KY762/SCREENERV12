"""Benchmarks: buy-and-hold arithmetic, and the random-selection distribution."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from screener.backtest.benchmarks import (
    buy_and_hold,
    date_matched_benchmark,
    random_benchmark,
    trade_entries,
    trade_returns,
)
from screener.backtest.engine import CostModel, Trade
from tests.unit.backtest.test_no_lookahead_backtest import synthetic

NO_COSTS = CostModel(slippage_bps=0.0)


def flat_then_up() -> pd.DataFrame:
    index = pd.bdate_range("2020-01-01", periods=4)
    return pd.DataFrame(
        {
            "open": [100.0, 100.0, 100.0, 100.0],
            "high": [110.0] * 4,
            "low": [90.0] * 4,
            "close": [100.0, 105.0, 110.0, 120.0],
            "volume": [1e6] * 4,
        },
        index=index,
    )


def test_buy_and_hold_is_first_open_to_last_close():
    got = buy_and_hold(flat_then_up(), date(2020, 1, 1), date(2030, 1, 1), NO_COSTS)
    assert got == pytest.approx(0.20)      # 100 -> 120


def test_buy_and_hold_respects_the_window():
    got = buy_and_hold(flat_then_up(), date(2020, 1, 1), date(2020, 1, 2), NO_COSTS)
    assert got == pytest.approx(0.05)      # 100 -> 105


def test_buy_and_hold_pays_slippage_both_ways():
    with_costs = buy_and_hold(flat_then_up(), date(2020, 1, 1), date(2030, 1, 1))
    assert with_costs < 0.20


def test_random_benchmark_is_reproducible_from_its_seed():
    bars = {f"S{i}": synthetic(i, n=400) for i in range(3)}
    kwargs = dict(
        start=date(2015, 1, 1), end=date(2030, 1, 1),
        n_trades=20, hold_periods=[5, 10], iterations=50, costs=NO_COSTS,
    )
    first = random_benchmark(bars, seed=7, **kwargs)
    second = random_benchmark(bars, seed=7, **kwargs)
    different = random_benchmark(bars, seed=8, **kwargs)

    assert np.array_equal(first.distribution, second.distribution)
    assert not np.array_equal(first.distribution, different.distribution)


def test_percentile_places_an_extreme_result_at_the_top():
    bars = {f"S{i}": synthetic(i, n=400) for i in range(3)}
    bench = random_benchmark(
        bars, start=date(2015, 1, 1), end=date(2030, 1, 1),
        n_trades=20, hold_periods=[5], iterations=200, seed=1, costs=NO_COSTS,
    )
    assert bench.percentile_of(10.0) == pytest.approx(100.0)   # +1000% per trade
    assert bench.percentile_of(-10.0) == pytest.approx(0.0)


def test_empty_universe_yields_an_empty_distribution_rather_than_an_error():
    bench = random_benchmark(
        {}, start=date(2015, 1, 1), end=date(2030, 1, 1),
        n_trades=10, hold_periods=[5], iterations=10,
    )
    assert bench.distribution.size == 0
    assert np.isnan(bench.percentile_of(0.5))


def test_trade_returns_are_fractional_on_the_entry_price():
    from decimal import Decimal
    trade = Trade(
        ticker="AAA", setup="t", entry_date=date(2020, 1, 1),
        entry_price=Decimal("100.00"), shares=10, stop=Decimal("95.00"),
        target=None, risk_dollars=Decimal("50"),
        exit_date=date(2020, 1, 5), exit_price=Decimal("110.00"), exit_reason="target",
    )
    assert trade_returns([trade]) == [pytest.approx(0.10)]


# --------------------------------------------------------------------------
# Date-matched benchmark
#
# The uniform benchmark picks its own entry dates, so it scores selection AND
# timing. Holding the calendar fixed is what makes a percentile a statement
# about the pick.
# --------------------------------------------------------------------------

def two_names_one_good_day() -> dict[str, pd.DataFrame]:
    """WINNER doubles on 2020-01-02; LOSER halves. Both trade every day."""
    index = pd.bdate_range("2020-01-01", periods=4)
    def frame(opens):
        return pd.DataFrame(
            {"open": opens, "high": [max(opens)] * 4, "low": [min(opens)] * 4,
             "close": opens, "volume": [1e6] * 4},
            index=index,
        )
    return {"WINNER": frame([100.0, 200.0, 200.0, 200.0]),
            "LOSER": frame([100.0, 50.0, 50.0, 50.0])}


def test_the_benchmark_only_buys_on_the_dates_the_strategy_traded():
    """A one-bar trade entered 2020-01-01 can only draw the two returns
    available that day (+100% and -50%), never a return from another date."""
    bench = date_matched_benchmark(
        two_names_one_good_day(),
        entries=[(date(2020, 1, 1), 1)],
        iterations=400, seed=1, costs=NO_COSTS,
    )

    assert bench.distribution.size == 400
    assert set(np.round(np.unique(bench.distribution), 6)) == {1.0, -0.5}


def test_picking_the_winner_every_time_ranks_above_random():
    strategy_return = 1.0                      # took WINNER on the good day
    bench = date_matched_benchmark(
        two_names_one_good_day(),
        entries=[(date(2020, 1, 1), 1)],
        iterations=400, seed=2, costs=NO_COSTS,
    )

    assert bench.percentile_of(strategy_return) > 40    # beat every LOSER draw
    assert bench.percentile_of(-0.5) == 0.0             # beat nothing


def test_a_trade_with_no_eligible_alternative_is_dropped_not_scored_zero():
    """Counting an unsampled trade as zero pulls the distribution toward zero,
    which flatters the strategy. `random_benchmark` divides by n_trades even
    when it skips a draw; this one divides by what it actually sampled."""
    bars = two_names_one_good_day()
    bench = date_matched_benchmark(
        bars,
        # Second entry is beyond the data, so no name is eligible for it.
        entries=[(date(2020, 1, 1), 1), (date(2029, 1, 1), 5)],
        iterations=200, seed=3, costs=NO_COSTS,
    )

    assert bench.n_trades == 1, "only the tradeable entry should be counted"
    assert set(np.round(np.unique(bench.distribution), 6)) == {1.0, -0.5}


def test_it_is_reproducible_from_its_seed():
    args = dict(entries=[(date(2020, 1, 1), 1)], iterations=100, costs=NO_COSTS)
    a = date_matched_benchmark(two_names_one_good_day(), seed=7, **args)
    b = date_matched_benchmark(two_names_one_good_day(), seed=7, **args)

    assert np.array_equal(a.distribution, b.distribution)


def test_no_entries_is_an_empty_distribution_rather_than_an_error():
    bench = date_matched_benchmark(two_names_one_good_day(), entries=[], iterations=50)
    assert bench.distribution.size == 0


def test_trade_entries_reports_the_calendar_of_closed_trades_only():
    closed = Trade(ticker="A", setup="s", entry_date=date(2020, 1, 1),
                   entry_price=Decimal("100"), shares=1, stop=Decimal("90"),
                   target=None, risk_dollars=Decimal("10"),
                   exit_date=date(2020, 1, 3), exit_price=Decimal("110"), bars_held=2)
    still_open = Trade(ticker="B", setup="s", entry_date=date(2020, 1, 1),
                       entry_price=Decimal("100"), shares=1, stop=Decimal("90"),
                       target=None, risk_dollars=Decimal("10"))

    assert trade_entries([closed, still_open]) == [(date(2020, 1, 1), 2)]


# --------------------------------------------------------------------------
# p-values
#
# A multiple-testing correction divides the significance level by the number
# of tests. That only works if the benchmark can state a small p honestly.
# --------------------------------------------------------------------------

def test_a_result_beyond_every_draw_is_not_p_zero():
    """Beating all 99 draws is p = 1/100, not 0: a finite Monte Carlo cannot
    rule out that a larger sample would have produced one that beat it."""
    from screener.backtest.benchmarks import RandomBenchmark

    bench = RandomBenchmark(99, 10, np.linspace(-0.01, 0.01, 99))
    assert bench.p_value(1.0) == pytest.approx(1 / 100)
    assert bench.smallest_p() == pytest.approx(1 / 100)


def test_p_value_counts_ties_against_the_strategy():
    """Ambiguity resolves against us (non-negotiable #6)."""
    from screener.backtest.benchmarks import RandomBenchmark

    bench = RandomBenchmark(3, 10, np.array([0.0, 0.0, 0.0]))
    assert bench.p_value(0.0) == pytest.approx(1.0)


def test_p_value_and_percentile_agree_away_from_the_tails():
    from screener.backtest.benchmarks import RandomBenchmark

    draws = np.linspace(0.0, 1.0, 1000)
    bench = RandomBenchmark(1000, 10, draws)
    assert bench.p_value(0.9) == pytest.approx(1 - bench.percentile_of(0.9) / 100, abs=0.002)


# --- the benchmark must draw from the strategy's own pool -------------------


def test_the_benchmark_can_be_restricted_to_a_universe():
    """Why `eligible` exists.

    Measured on H1's twelve-month configuration, 2026-09-22: unrestricted on
    both sides it sat at the 97.7th percentile against random; restricted on
    the strategy side alone it read the 31.3rd. Neither was the right test.
    The pool of all stored symbols is enriched with companies that later GREW
    into the index, so leaving the benchmark unrestricted hands it that
    enrichment and takes it from the strategy.
    """
    index = pd.bdate_range("2020-01-02", periods=30)
    flat = pd.DataFrame(
        {"open": np.full(30, 100.0), "high": np.full(30, 101.0),
         "low": np.full(30, 99.0), "close": np.full(30, 100.0),
         "volume": np.full(30, 1e6)},
        index=index,
    )
    doubler = flat.copy()
    doubler["open"] = np.linspace(100.0, 200.0, 30)

    bars = {"MEMBER": flat, "OUTSIDER": doubler}
    entries = [(index[0].date(), 10)]

    everything = date_matched_benchmark(bars, entries=entries, iterations=200, seed=1)
    members_only = date_matched_benchmark(
        bars, entries=entries, iterations=200, seed=1,
        eligible=lambda ticker, _day: ticker == "MEMBER",
    )

    # OUTSIDER rises through the window, so a pool containing it has a higher
    # mean than one restricted to the flat member.
    assert everything.distribution.mean() > members_only.distribution.mean()
    assert members_only.distribution.mean() == pytest.approx(0.0, abs=0.002)


def test_an_empty_universe_on_a_date_drops_that_trade_from_both_sides():
    """A trade with no eligible alternative is dropped rather than scored as
    zero: dividing by trades that were never sampled pulls the distribution
    toward zero and flatters the strategy."""
    index = pd.bdate_range("2020-01-02", periods=30)
    flat = pd.DataFrame(
        {"open": np.full(30, 100.0), "high": np.full(30, 101.0),
         "low": np.full(30, 99.0), "close": np.full(30, 100.0),
         "volume": np.full(30, 1e6)},
        index=index,
    )

    bench = date_matched_benchmark(
        {"A": flat, "B": flat}, entries=[(index[0].date(), 10)],
        iterations=50, seed=1, eligible=lambda *_: False,
    )

    assert bench.n_trades == 0
    assert bench.distribution.size == 0
