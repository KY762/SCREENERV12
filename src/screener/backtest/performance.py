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


def by_regime(
    trades: list[Trade], starting_equity: float | Decimal = 10_000
) -> dict[str, Stats]:
    """Per-regime statistics. Buckets with no trades are absent, not zero --
    'no evidence' and 'no edge' are different findings.

    ``total_return_pct`` here is a genuine RETURN: the bucket's P&L divided by
    starting equity. It previously held a sum of R multiples, which the
    robustness criterion then compared against a -15% floor and printed as a
    percentage -- so a bucket at -197 R displayed as "-19725.7%". The units have
    to match the threshold they are tested against.
    """
    equity = float(starting_equity) or 1.0
    buckets: dict[str, list[Trade]] = {}
    for trade in trades:
        if trade.exit_date is None or trade.r_multiple is None:
            continue
        name = regime_for(trade.entry_date)
        if name is None:
            continue
        buckets.setdefault(name, []).append(trade)
    return {
        name: _bucket_stats(bucket, equity) for name, bucket in sorted(buckets.items())
    }


def _bucket_stats(bucket: list[Trade], equity: float) -> Stats:
    r_values = [t.r_multiple for t in bucket if t.r_multiple is not None]
    pnls = [float(t.pnl) for t in bucket]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_loss = -sum(losses)
    return Stats(
        trades=len(bucket),
        wins=len(wins),
        losses=len(losses),
        win_rate=len(wins) / len(bucket) if bucket else 0.0,
        expectancy_r=sum(r_values) / len(r_values) if r_values else 0.0,
        expectancy_dollars=sum(pnls) / len(pnls) if pnls else 0.0,
        profit_factor=(sum(wins) / gross_loss) if gross_loss > 0 else float("inf"),
        gross_profit=sum(wins),
        gross_loss=gross_loss,
        max_drawdown_pct=0.0,
        # P&L as a fraction of starting equity -- the unit the -15% floor is in.
        total_return_pct=sum(pnls) / equity,
        avg_bars_held=(
            sum(t.bars_held for t in bucket) / len(bucket) if bucket else 0.0
        ),
        exits={},
    )


# --------------------------------------------------------------------------
# Pre-registered criteria -- docs/03-HYPOTHESES.md 0.6, amended 2026-09-19
# --------------------------------------------------------------------------
#
# Amended by the operator on 2026-09-19, before any validation or test run
# existed, to make every criterion measure the same thing -- whether the rule
# PICKS well -- rather than a mix of picking, market direction and timing:
#
#   trade count     effective observations, not raw trades. Positions held at
#                   the same time in correlated names are not independent, and
#                   the raw count let through configurations holding ~150
#                   independent observations (backtest/inference.py).
#   vs random       random names bought on the SAME DAYS (date-matched), as a
#                   one-sided p-value, against a family-wise 5% corrected by
#                   Holm across the validation family. Was: any-day random,
#                   above the 75th percentile -- which a rule with no skill
#                   passes one time in four and which charged timing as skill.
#   regimes         beat random within at least 2 of the split's 3 regime
#                   buckets, and no bucket losing more than 15%. Was: positive
#                   return in "3 of 5" buckets, which ran as "all 3" because
#                   no split contains 5, and which for a long-only rule tested
#                   whether the market rose through the 2018-Q4 correction.
#
# The thresholds are constants for the reason they always were: a threshold
# that can be passed in can be moved after seeing the number.

MIN_EFFECTIVE_TRADES = 200
MIN_PROFIT_FACTOR = 1.20
MAX_DRAWDOWN = 0.25
REGIME_BUCKETS_BEATEN = (2, 3)        # beat random in >= 2 of a split's 3 buckets
WORST_REGIME_FLOOR = -0.15            # no bucket worse than -15%
FAMILY_WISE_ALPHA = 0.05              # Holm across the validation family


@dataclass(frozen=True)
class CriterionResult:
    name: str
    passed: bool
    observed: str
    required: str


@dataclass(frozen=True)
class RegimeResult:
    """One regime bucket: what the strategy did there, and whether random
    names bought on the same days did better."""

    name: str
    trades: int
    total_return_pct: float
    same_day_percentile: float | None     # None: benchmark not run

    @property
    def beat_random(self) -> bool:
        # Ambiguity resolves against us: an unranked bucket is not a win.
        return self.same_day_percentile is not None and self.same_day_percentile > 50.0


def check_criteria(
    stats: Stats,
    *,
    effective_trades: float | None,
    regimes: dict[str, RegimeResult],
    regime_buckets_in_split: int,
    same_day_p: float | None,
    alpha: float = FAMILY_WISE_ALPHA,
) -> list[CriterionResult]:
    """Apply the pre-registered criteria. Returns one row per criterion.

    Every criterion is reported, passed or failed, rather than short-circuiting
    on the first failure -- 'failed on trade count' and 'failed on everything'
    call for different revisions.

    `alpha` is the significance level THIS run is held to. On development it
    is the family-wise 5% (no family exists there). On an evidential split the
    caller passes 5% / m, m being the size of the validation family: that is
    the first and strictest step of Holm, so a run that clears it clears Holm
    whatever the rest of the family does. A run that misses it may still clear
    Holm's later steps -- `screener prereg family` gives the final verdict
    once every registered test has run.

    `regime_buckets_in_split` is the denominator for the regime criterion, so
    a bucket the strategy never traded in counts as not beaten rather than
    shrinking the denominator.
    """
    need_beaten, of = REGIME_BUCKETS_BEATEN
    required_beaten = -(-need_beaten * regime_buckets_in_split // of)   # ceil
    beaten = sum(1 for r in regimes.values() if r.beat_random)
    worst = min((r.total_return_pct for r in regimes.values()), default=0.0)

    eff = "not estimable" if effective_trades is None else f"{effective_trades:,.0f}"
    results = [
        CriterionResult(
            "trade_count",
            effective_trades is not None and effective_trades >= MIN_EFFECTIVE_TRADES,
            f"{eff} effective ({stats.trades:,} raw)",
            f">= {MIN_EFFECTIVE_TRADES} effective",
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
            regime_buckets_in_split > 0
            and beaten >= required_beaten
            and worst >= WORST_REGIME_FLOOR,
            f"beat random in {beaten} of {regime_buckets_in_split}, worst {worst:+.1%}",
            f">= {required_beaten} of {regime_buckets_in_split}, "
            f"none < {WORST_REGIME_FLOOR:.0%}",
        ),
    ]
    if same_day_p is None:
        results.append(CriterionResult(
            "vs_random", False, "not run", f"same-day p <= {alpha:.4g}",
        ))
    else:
        results.append(CriterionResult(
            "vs_random", same_day_p <= alpha,
            f"same-day p = {same_day_p:.4f}", f"<= {alpha:.4g}",
        ))
    return results


def holm(p_values: dict[str, float], alpha: float = FAMILY_WISE_ALPHA) -> dict[str, bool]:
    """Holm's step-down procedure (Holm 1979): which tests in a family pass.

    Sort ascending; the k-th smallest (from 0) must be <= alpha / (m - k), and
    the first to fail stops everything after it. Controls the chance of even
    one false pass across the family at `alpha`, with no assumption about how
    the tests relate -- uniformly more powerful than Bonferroni, never less.
    """
    m = len(p_values)
    verdict = {name: False for name in p_values}
    for k, (name, p) in enumerate(sorted(p_values.items(), key=lambda kv: kv[1])):
        if p > alpha / (m - k):
            break
        verdict[name] = True
    return verdict


def split_regime_count(start: date, end: date) -> int:
    """How many regime buckets fall wholly or partly inside a split."""
    from .splits import REGIMES

    return sum(1 for r in REGIMES if r.start <= end and r.end >= start)


def all_passed(results: list[CriterionResult]) -> bool:
    return all(r.passed for r in results)


def total_pnl(trades: list[Trade]) -> Decimal:
    return sum((t.pnl for t in trades), Decimal("0"))


def trade_dates(trades: list[Trade]) -> list[date]:
    return [t.entry_date for t in trades]
