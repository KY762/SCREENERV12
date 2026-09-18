"""Benchmarks -- what a result has to beat before it means anything.

A strategy that made money is not evidence. The questions that matter are:

    Did it beat doing nothing?          -> buy-and-hold
    Did SELECTION add anything at all?  -> random selection

The random benchmark is the important one and the one usually omitted. It draws
trades from the same universe, over the same window, with the same holding
periods, choosing symbols and dates at random. If the strategy cannot beat that
distribution, its rules are decoration on top of plain market exposure -- the
edge, if any, was in being long, not in choosing.

There are two of them, and they answer different questions:

    random_benchmark        symbol AND entry date random. Prices selection and
                            timing together. A strategy that only traded in
                            good weeks scores well here for a reason that is
                            not selection.
    date_matched_benchmark  entry dates held to the strategy's own, only the
                            symbol swapped. Timing is now identical on both
                            sides, so what is left is the pick.

Report both. The gap between them IS the timing contribution, which no single
number can separate.
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


def trade_entries(trades: Sequence[Trade]) -> list[tuple[date, int]]:
    """(entry date, bars held) for every closed trade -- the calendar to match."""
    return [
        (t.entry_date, t.bars_held)
        for t in trades
        if t.exit_date is not None and t.bars_held > 0
    ]


def date_matched_benchmark(
    bars_by_symbol: dict[str, pd.DataFrame],
    *,
    entries: Sequence[tuple[date, int]],
    iterations: int = 1000,
    seed: int = 0,
    costs: CostModel | None = None,
) -> RandomBenchmark:
    """Mean per-trade return when only the SYMBOL is chosen at random.

    Every real trade contributes its own entry date and holding length. Each
    iteration buys a different random name on that same day and holds it the
    same number of bars, so the calendar is identical on both sides and the
    only difference left is which symbol was picked.

    `random_benchmark` samples entry dates uniformly across the window, which
    bundles selection with timing: a strategy whose signals cluster in strong
    weeks beats it without picking anything well, and one whose signals cluster
    in a drawdown loses to it while picking fine. Neither says what the report
    claims a percentile says. This is the one to quote for "did selection add
    anything".

    Eligibility is "had a bar that day, with enough bars after it". That is
    tradeability as this database sees it, NOT point-in-time index membership,
    which is not threaded this far down -- so the pool can include a name that
    was listed but outside the universe on that date.

    A trade with no eligible alternative is dropped from BOTH sides rather than
    counted as zero: dividing by trades that were never sampled pulls the
    distribution toward zero and flatters the strategy.
    """
    costs = costs or CostModel()
    slip = costs.slippage_bps / 10_000.0
    rng = np.random.default_rng(seed)

    frames = {t: f for t, f in bars_by_symbol.items() if len(f) > 1}
    if not frames or not entries:
        return RandomBenchmark(iterations, 0, np.array([], dtype="float64"))

    # One aligned matrix of opens, dates x symbols, NaN where a name has no bar
    # that day. Turns "every eligible symbol on date d" into one vectorised row
    # lookup instead of a dict probe per symbol per trade.
    all_dates = sorted({d for f in frames.values() for d in f.index})
    row_of = {d.date(): i for i, d in enumerate(all_dates)}
    opens = np.full((len(all_dates), len(frames)), np.nan, dtype="float64")
    for col, frame in enumerate(frames.values()):
        idx = np.fromiter((row_of[d.date()] for d in frame.index), dtype="int64",
                          count=len(frame.index))
        opens[idx, col] = frame["open"].to_numpy(dtype="float64")

    # Trades sharing a date and horizon draw from the same pool, so build it once.
    groups: dict[tuple[date, int], int] = {}
    for entry_date, hold in entries:
        if hold > 0:
            groups[(entry_date, hold)] = groups.get((entry_date, hold), 0) + 1

    totals = np.zeros(iterations, dtype="float64")
    counted = 0
    for (entry_date, hold), n in groups.items():
        i = row_of.get(entry_date)
        if i is None or i + hold >= len(all_dates):
            continue
        buy, sell = opens[i], opens[i + hold]
        usable = np.isfinite(buy) & np.isfinite(sell) & (buy > 0)
        if not usable.any():
            continue
        entry = buy[usable] * (1.0 + slip)
        pool = (sell[usable] * (1.0 - slip) - entry) / entry
        totals += rng.choice(pool, size=(iterations, n), replace=True).sum(axis=1)
        counted += n

    if counted == 0:
        return RandomBenchmark(iterations, 0, np.array([], dtype="float64"))
    return RandomBenchmark(iterations, counted, totals / counted)


def trade_return(trade: Trade) -> float | None:
    """One trade's fractional return on its entry price, or None if unclosed.

    Percent rather than R, because the random benchmark has no stop and
    therefore no R. Comparisons need a unit both sides can express. The single
    definition every benchmark and diagnostic uses.
    """
    if trade.exit_price is None or trade.entry_price <= 0:
        return None
    return float((trade.exit_price - trade.entry_price) / trade.entry_price)


def trade_returns(trades: Sequence[Trade]) -> list[float]:
    """Per-trade fractional returns for every closed trade."""
    return [r for r in (trade_return(t) for t in trades) if r is not None]


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
