"""Shared execution path for a single backtest configuration.

Extracted so that ``screener backtest run`` and ``screener backtest surface``
cannot drift apart. A surface built by a second, similar-looking code path
would be comparing cells against a baseline computed slightly differently, and
the difference would look like a parameter effect.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..calc.sizing import RiskLimits
from ..db.models import Symbol
from ..metrics.compute import load_bars
from .benchmarks import random_benchmark, trade_returns
from .engine import Candidate, CostModel, ExitRule, run_backtest
from .performance import Stats, by_regime, check_criteria, summarize
from .splits import Split
from .strategies import (
    TrendFilter,
    always_in_universe,
    pattern_candidates,
    relative_strength_candidates,
)

HYPOTHESES = ("h1", "h2", "h3", "h4")


@dataclass(frozen=True)
class RunConfig:
    """Everything that defines one configuration. Hashed into the research log,
    so two runs with the same config are recognised as the same spend."""

    hypothesis: str
    equity: float = 10_000.0
    r_multiple: float | None = None
    time_limit: int | None = None
    slippage_bps: float = 5.0
    trend_filter: bool = True
    # Whether a stop is used at all. Not a tuning knob -- a structural question.
    # If removing the stop turns a losing configuration profitable, the entry
    # rule was never the problem and the exit design is what costs.
    use_stop: bool = True
    displacement: float | None = None
    hold: int = 5
    top_pct: float = 0.10
    stop_atr: float = 2.0
    rs_lookback: int = 63
    sweep_lookback: int = 10
    # Portfolio constraints. Defaults are the approved profile values; raising
    # them is how an exit-rule comparison is freed from the slot competition
    # that otherwise decides which signals each arm gets to take.
    max_positions: int = 5
    max_open_risk_pct: float = 0.05
    risk_pct_per_trade: float = 0.01
    max_position_pct: float = 0.25

    def __post_init__(self) -> None:
        if not self.use_stop and self.time_limit == 0:
            raise ValueError("a configuration with no stop needs a time limit")

    def resolved(self) -> RunConfig:
        """Apply per-hypothesis defaults from the specification.

        H1 (docs/03) exits on time or stop and has no profit target; the
        pattern hypotheses surface over R targets. One shared default would
        test something no specification describes.
        """
        time_limit = self.time_limit
        if time_limit is None:
            time_limit = self.hold if self.hypothesis == "h1" else 10
        r_multiple = self.r_multiple
        if r_multiple is None and self.hypothesis != "h1":
            r_multiple = 2.0
        return RunConfig(**{**self.__dict__, "time_limit": time_limit, "r_multiple": r_multiple})

    def as_dict(self) -> dict[str, Any]:
        data = dict(self.__dict__)
        if self.hypothesis != "h1":
            for key in ("stop_atr", "rs_lookback", "top_pct", "hold"):
                data.pop(key, None)
        if self.hypothesis != "h2":
            data.pop("displacement", None)
        if self.hypothesis != "h3":
            data.pop("sweep_lookback", None)
        return data


@dataclass
class Outcome:
    config: RunConfig
    stats: Stats
    regimes: dict[str, Stats]
    candidates: int
    rejected: dict[str, int]
    random_percentile: float | None
    criteria: list = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.criteria) and all(c.passed for c in self.criteria)


def load_symbol_bars(session: Session, symbols: str | None) -> dict[str, pd.DataFrame]:
    stmt = select(Symbol).order_by(Symbol.ticker)
    if symbols:
        wanted = [t.strip().upper() for t in symbols.split(",") if t.strip()]
        stmt = stmt.where(Symbol.ticker.in_(wanted))
    rows = [(s.id, s.ticker) for s in session.scalars(stmt)]
    bars = {ticker: load_bars(session, sid) for sid, ticker in rows}
    return {k: v for k, v in bars.items() if not v.empty}


def build_candidates(
    bars_by_symbol: dict[str, pd.DataFrame],
    config: RunConfig,
    universe=always_in_universe,
) -> list[Candidate]:
    """Signal generation. Depends only on the entry-side parameters, so a
    surface that varies exit rules can reuse one call across every cell."""
    trend = TrendFilter(enabled=config.trend_filter)
    if config.hypothesis == "h1":
        return relative_strength_candidates(
            bars_by_symbol, trend=trend, rebalance_days=config.hold,
            top_pct=config.top_pct, stop_atr=config.stop_atr,
            lookback=config.rs_lookback, universe=universe,
        )
    extra: dict[str, Any] = {}
    if config.hypothesis == "h2":
        extra["displacement_min"] = config.displacement
    if config.hypothesis == "h3":
        extra["n_bar"] = config.sweep_lookback
    return pattern_candidates(
        bars_by_symbol, hypothesis=config.hypothesis, trend=trend,
        universe=universe, **extra,
    )


def evaluate(
    candidates: list[Candidate],
    bars_by_symbol: dict[str, pd.DataFrame],
    config: RunConfig,
    split: Split,
    *,
    random_iterations: int = 1000,
    seed: int = 0,
) -> Outcome:
    """Run one configuration and score it against the pre-registered criteria."""
    config = config.resolved()
    costs = CostModel(slippage_bps=config.slippage_bps)

    result = run_backtest(
        candidates, bars_by_symbol,
        start=split.start, end=split.end,
        starting_equity=config.equity,
        limits=RiskLimits(
            risk_pct_per_trade=Decimal(str(config.risk_pct_per_trade)),
            max_position_pct=Decimal(str(config.max_position_pct)),
            max_concurrent_positions=config.max_positions,
            max_total_open_risk_pct=Decimal(str(config.max_open_risk_pct)),
        ),
        exit_rule=ExitRule(
            r_multiple=config.r_multiple,
            time_limit=config.time_limit,
            use_stop=config.use_stop,
        ),
        costs=costs,
    )

    stats = summarize(result)
    regimes = by_regime(result.trades, config.equity)

    percentile = None
    holds = [t.bars_held for t in result.closed_trades if t.bars_held > 0]
    if holds and random_iterations > 0:
        bench = random_benchmark(
            bars_by_symbol, start=split.start, end=split.end,
            n_trades=len(holds), hold_periods=holds,
            iterations=random_iterations, seed=seed, costs=costs,
        )
        observed = trade_returns(result.closed_trades)
        percentile = bench.percentile_of(
            sum(observed) / len(observed) if observed else 0.0
        )

    return Outcome(
        config=config,
        stats=stats,
        regimes=regimes,
        candidates=len(candidates),
        rejected=result.rejected,
        random_percentile=percentile,
        criteria=check_criteria(stats, regimes, percentile),
    )


def universe_filter(session: Session, universe_name: str | None):
    """Point-in-time membership predicate, with per-date caching."""
    if universe_name is None:
        return always_in_universe

    from ..universe.build import universe_members

    cache: dict[date, set[str]] = {}

    def predicate(ticker: str, day: date) -> bool:
        if day not in cache:
            cache[day] = set(universe_members(session, universe_name, day))
        return ticker in cache[day]

    return predicate
