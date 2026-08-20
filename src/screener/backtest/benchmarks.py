"""Benchmarks -- what a result has to beat before it means anything.

A strategy that made money is not evidence. The questions that matter are:

    Did it beat doing nothing?          -> buy-and-hold
    Did SELECTION add anything at all?  -> random selection

The random benchmark is the important one and the one usually omitted. It draws
trades from the same universe, over the same window, with the same holding
periods, choosing symbols and dates at random. If the strategy cannot beat that
distribution, its rules are decoration on top of plain market exposure -- the
edge, if any, was in being long, not in choosing.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd

from .engine import CostModel, Trade


def trade_returns(trades: Sequence[Trade]) -> list[float]:
    """Per-trade fractional return on the entry price.

    Percent rather than R, because the random benchmark has no stop and
    therefore no R. Comparisons need a unit both sides can express.
    """
    out = []
    for trade in trades:
        if trade.exit_price is None or trade.entry_price <= 0:
            continue
        out.append(float((trade.exit_price - trade.entry_price) / trade.entry_price))
    return out


def buy_and_hold(
    bars: pd.DataFrame, start: date, end: date, costs: CostModel | None = None
) -> float:
    """Fractional return from buying the first open in the window and holding."""
    costs = costs or CostModel()
    window = bars.loc[
        (bars.index >= pd.Timestamp(start)) & (bars.index <= pd.Timestamp(end))
    ]
    if len(window) < 2:
        return 0.0

    entry = costs.buy_fill(Decimal(str(window.iloc[0]["open"])))
    exit_ = costs.sell_fill(Decimal(str(window.iloc[-1]["close"])))
    return float((exit_ - entry) / entry)


@dataclass(frozen=True)
class RandomBenchmark:
    iterations: int
    n_trades: int
    distribution: np.ndarray        # mean per-trade return, one entry per iteration

    def percentile_of(self, observed: float) -> float:
        """Where the observed mean return sits in the random distribution."""
        if self.distribution.size == 0:
            return float("nan")
        return float((self.distribution < observed).mean() * 100.0)

    def describe(self, observed: float) -> str:
        pct = self.percentile_of(observed)
        return (
            f"random: median {np.median(self.distribution):+.3%}, "
            f"95th {np.percentile(self.distribution, 95):+.3%} | "
            f"strategy {observed:+.3%} = {pct:.1f}th percentile"
        )


def random_benchmark(
    bars_by_symbol: dict[str, pd.DataFrame],
    *,
    start: date,
    end: date,
    n_trades: int,
    hold_periods: Sequence[int],
    iterations: int = 1000,
    seed: int = 0,
    costs: CostModel | None = None,
) -> RandomBenchmark:
    """Distribution of mean per-trade return under random selection.

    ``hold_periods`` should be the strategy's own observed holding periods, so
    the benchmark is matched on horizon and the comparison isolates selection.

    Seeded: the same inputs give the same distribution, so a result can be
    re-derived later rather than taken on trust.
    """
    costs = costs or CostModel()
    rng = random.Random(seed)

    pools: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for ticker, frame in bars_by_symbol.items():
        window = frame.loc[
            (frame.index >= pd.Timestamp(start)) & (frame.index <= pd.Timestamp(end))
        ]
        if len(window) < 2:
            continue
        pools[ticker] = (
            window["open"].to_numpy(dtype="float64"),
            window["close"].to_numpy(dtype="float64"),
        )

    if not pools or n_trades <= 0 or not hold_periods:
        return RandomBenchmark(iterations, n_trades, np.array([], dtype="float64"))

    tickers = sorted(pools)
    slip = costs.slippage_bps / 10_000.0
    means = np.empty(iterations, dtype="float64")

    for it in range(iterations):
        total = 0.0
        for _ in range(n_trades):
            ticker = rng.choice(tickers)
            opens, _closes = pools[ticker]
            hold = rng.choice(list(hold_periods))
            last_valid = len(opens) - hold - 1
            if last_valid < 0:
                continue
            i = rng.randint(0, last_valid)
            entry = opens[i] * (1.0 + slip)
            exit_ = opens[i + hold] * (1.0 - slip)
            total += (exit_ - entry) / entry
        means[it] = total / n_trades

    return RandomBenchmark(iterations, n_trades, means)
