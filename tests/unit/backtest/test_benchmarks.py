"""Benchmarks: buy-and-hold arithmetic, and the random-selection distribution."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from screener.backtest.benchmarks import (
    buy_and_hold,
    random_benchmark,
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
