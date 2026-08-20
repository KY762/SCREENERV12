"""Performance statistics and the pre-registered criteria check.

The thresholds in ``CRITERIA`` are the ones fixed in docs/03-HYPOTHESES.md 0.6
BEFORE any result existed. They are constants here, not arguments, because a
threshold you can pass in is a threshold you can move after seeing the number.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pandas as pd

from .engine import BacktestResult, Trade
from .splits import regime_for


@dataclass(frozen=True)
class Stats:
    trades: int
    wins: int
    losses: int
    win_rate: float
    expectancy_r: float          # mean R per trade -- the headline number
    expectancy_dollars: float
    profit_factor: float
    gross_profit: float
    gross_loss: float
    max_drawdown_pct: float
    total_return_pct: float
    avg_bars_held: float
    exits: dict[str, int]

    def describe(self) -> str:
        return (
            f"{self.trades} trades, {self.win_rate:.1%} win rate, "
            f"expectancy {self.expectancy_r:+.3f}R, PF {self.profit_factor:.2f}, "
            f"maxDD {self.max_drawdown_pct:.1%}, return {self.total_return_pct:+.1%}"
        )


def max_drawdown(curve: pd.Series) -> float:
    """Largest peak-to-trough decline in the equity curve, as a fraction."""
    if curve.empty:
        return 0.0
    running_peak = curve.cummax()
    drawdown = (curve - running_peak) / running_peak
    return float(-drawdown.min())


def summarize(result: BacktestResult) -> Stats:
    closed = result.closed_trades
    r_values = [t.r_multiple for t in closed if t.r_multiple is not None]
    pnls = [float(t.pnl) for t in closed]

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_profit = sum(wins)
    gross_loss = -sum(losses)

    exits: dict[str, int] = {}
    for trade in closed:
        key = trade.exit_reason or "unknown"
        exits[key] = exits.get(key, 0) + 1

    start = float(result.starting_equity)
    return Stats(
        trades=len(closed),
        wins=len(wins),
        losses=len(losses),
        win_rate=len(wins) / len(closed) if closed else 0.0,
        expectancy_r=sum(r_values) / len(r_values) if r_values else 0.0,
        expectancy_dollars=sum(pnls) / len(pnls) if pnls else 0.0,
        # An infinite profit factor is not a good result, it is too few trades.
        profit_factor=(gross_profit / gross_loss) if gross_loss > 0 else float("inf"),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        max_drawdown_pct=max_drawdown(result.equity_curve),
        total_return_pct=(float(result.ending_equity) - start) / start if start else 0.0,
        avg_bars_held=(
            sum(t.bars_held for t in closed) / len(closed) if closed else 0.0
        ),
        exits=exits,
    )


def by_regime(trades: list[Trade]) -> dict[str, Stats | None]:
    """Per-regime totals in R. Buckets with no trades report None, not zero --
    'no evidence' and 'no edge' are different findings."""
    buckets: dict[str, list[float]] = {}
    for trade in trades:
        if trade.exit_date is None or trade.r_multiple is None:
            continue
        name = regime_for(trade.entry_date)
        if name is None:
            continue
        buckets.setdefault(name, []).append(trade.r_multiple)
    return {
        name: _r_only_stats(values) for name, values in sorted(buckets.items())
    }


def _r_only_stats(r_values: list[float]) -> Stats:
    wins = [r for r in r_values if r > 0]
    losses = [r for r in r_values if r < 0]
    gross_loss = -sum(losses)
    return Stats(
        trades=len(r_values),
        wins=len(wins),
        losses=len(losses),
        win_rate=len(wins) / len(r_values) if r_values else 0.0,
        expectancy_r=sum(r_values) / len(r_values) if r_values else 0.0,
        expectancy_dollars=0.0,
        profit_factor=(sum(wins) / gross_loss) if gross_loss > 0 else float("inf"),
        gross_profit=sum(wins),
        gross_loss=gross_loss,
        max_drawdown_pct=0.0,
        total_return_pct=sum(r_values),
        avg_bars_held=0.0,
        exits={},
    )


# --------------------------------------------------------------------------
# Pre-registered criteria -- docs/03-HYPOTHESES.md 0.6
# --------------------------------------------------------------------------

MIN_TRADES = 200
MIN_PROFIT_FACTOR = 1.20
MAX_DRAWDOWN = 0.25
MIN_REGIME_BUCKETS_POSITIVE = 3
WORST_REGIME_FLOOR = -0.15          # no bucket worse than -15%


@dataclass(frozen=True)
class CriterionResult:
    name: str
    passed: bool
    observed: str
    required: str


def check_criteria(
    stats: Stats,
    regimes: dict[str, Stats | None],
    random_percentile: float | None = None,
) -> list[CriterionResult]:
    """Apply the pre-registered criteria. Returns one row per criterion.

    Every criterion is reported, passed or failed, rather than short-circuiting
    on the first failure -- 'failed on trade count' and 'failed on everything'
    call for different revisions.
    """
    positive_buckets = sum(
        1 for s in regimes.values() if s is not None and s.expectancy_r > 0
    )
    worst = min(
        (s.total_return_pct for s in regimes.values() if s is not None),
        default=0.0,
    )

    results = [
        CriterionResult(
            "trade_count", stats.trades >= MIN_TRADES,
            f"{stats.trades}", f">= {MIN_TRADES}",
        ),
        CriterionResult(
            "expectancy", stats.expectancy_r > 0,
            f"{stats.expectancy_r:+.3f}R", "> 0",
        ),
        CriterionResult(
            "profit_factor", stats.profit_factor > MIN_PROFIT_FACTOR,
            f"{stats.profit_factor:.2f}", f"> {MIN_PROFIT_FACTOR}",
        ),
        CriterionResult(
            "max_drawdown", stats.max_drawdown_pct < MAX_DRAWDOWN,
            f"{stats.max_drawdown_pct:.1%}", f"< {MAX_DRAWDOWN:.0%}",
        ),
        CriterionResult(
            "regime_robustness",
            positive_buckets >= MIN_REGIME_BUCKETS_POSITIVE and worst >= WORST_REGIME_FLOOR,
            f"{positive_buckets} positive, worst {worst:+.1%}",
            f">= {MIN_REGIME_BUCKETS_POSITIVE} positive, none < {WORST_REGIME_FLOOR:.0%}",
        ),
    ]
    if random_percentile is not None:
        results.append(
            CriterionResult(
                "vs_random", random_percentile > 75.0,
                f"{random_percentile:.1f}th pct", "> 75th pct",
            )
        )
    else:
        results.append(
            CriterionResult(
                "vs_random", False, "not run", "> 75th pct of 1,000 iterations",
            )
        )
    return results


def all_passed(results: list[CriterionResult]) -> bool:
    return all(r.passed for r in results)


def total_pnl(trades: list[Trade]) -> Decimal:
    return sum((t.pnl for t in trades), Decimal("0"))


def trade_dates(trades: list[Trade]) -> list[date]:
    return [t.entry_date for t in trades]
