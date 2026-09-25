"""Shared execution path for a single backtest configuration.

Extracted so that ``screener backtest run`` and ``screener backtest surface``
cannot drift apart. A surface built by a second, similar-looking code path
would be comparing cells against a baseline computed slightly differently, and
the difference would look like a parameter effect.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..calc.sizing import RiskLimits
from ..calc.spread import spread_table
from ..db.models import Symbol
from ..ingest.actions import load_splits_bulk
from ..metrics.compute import load_bars
from ..universe import quarantine
from . import inference
from .benchmarks import (
    date_matched_benchmark,
    random_benchmark,
    trade_entries,
    trade_return,
)
from .engine import Candidate, CostModel, ExitRule, run_backtest
from .performance import (
    FAMILY_WISE_ALPHA,
    RegimeResult,
    Stats,
    by_regime,
    check_criteria,
    split_regime_count,
    summarize,
)
from .splits import Split, regime_for
from .strategies import (
    TrendFilter,
    always_in_universe,
    canonical_momentum_candidates,
    drift_candidates,
    pattern_candidates,
    relative_strength_candidates,
)

log = logging.getLogger(__name__)

# h1-h4 are Round 1. h5-h7 are Round 2, admitted after Round 1 returned no
# positive configuration -- each chosen for having published evidence behind
# it rather than for looking promising in our own failed results.
HYPOTHESES = ("h1", "h2", "h3", "h4", "h5", "h6", "h7")

ROUND_2 = ("h5", "h6", "h7")

# Holding period per hypothesis, in trading days. H5 is momentum 12-1, which
# the literature holds for months and whose `monthly_rebalance` flag says the
# same. The pattern hypotheses do not read `hold` at all -- they exit on
# `time_limit` -- so their entry exists only to keep the mapping total.
#
# H1 was 5 until 2026-09-18, when the operator narrowed it to swing holds of
# 10-20 trading days with 20 as the default (docs/03 §H1 amendment). Made
# AFTER seeing development results, where 3- and 5-day holds sat near zero
# expectancy; Jegadeesh & Titman (1993) also find the momentum return absent in
# the month after ranking. The 3/5-day runs already logged remain counted.
HOLD_DEFAULTS: dict[str, int] = {
    "h1": 20, "h2": 5, "h3": 5, "h4": 5,
    "h5": 21,
    "h6": 5, "h7": 5,
}


@dataclass(frozen=True)
class RunConfig:
    """Everything that defines one configuration. Hashed into the research log,
    so two runs with the same config are recognised as the same spend."""

    hypothesis: str
    equity: float = 10_000.0
    r_multiple: float | None = None
    time_limit: int | None = None
    slippage_bps: float = 5.0
    # Charge each symbol its OWN measured spread rather than the flat rate.
    #
    # Default True as of 2026-09-24. The flat 5bp a side was never measured and
    # understates the mid/small-cap universe by roughly 2.7x: the median symbol
    # above the $2M dollar-volume floor runs a 27bp round trip on development
    # against the 10bp charged. Every result produced before this date assumed
    # trading was cheaper than it is, which flattered them -- all of them still
    # failed, so no verdict reverses, but a marginal one would have died here.
    #
    # This is part of the configuration and therefore part of its hash: a run
    # with measured costs is not the same experiment as one without. No
    # validation or test slot had been spent and no pre-registration was signed
    # when it changed, so nothing already paid for was invalidated.
    measured_spreads: bool = True
    trend_filter: bool = True
    # Whether a stop is used at all. Not a tuning knob -- a structural question.
    # If removing the stop turns a losing configuration profitable, the entry
    # rule was never the problem and the exit design is what costs.
    use_stop: bool = True
    displacement: float | None = None
    # None means "use this hypothesis's own horizon" -- see HOLD_DEFAULTS.
    hold: int | None = None
    top_pct: float = 0.10
    stop_atr: float = 2.0
    rs_lookback: int = 63
    sweep_lookback: int = 10
    # Portfolio constraints. Defaults are the approved profile values; raising
    # them is how an exit-rule comparison is freed from the slot competition
    # that otherwise decides which signals each arm gets to take.
    max_positions: int = 5
    max_open_risk_pct: float = 0.05
    # Round 2
    mom_lookback: int = 252
    mom_skip: int = 21
    monthly_rebalance: bool = True
    reaction_pct: float = 0.03
    entry_delay: int = 1
    squeeze_percentile: float = 0.20
    squeeze_window: int = 126
    breakout_window: int = 20
    risk_pct_per_trade: float = 0.01
    max_position_pct: float = 0.25
    #: Ratchet the stop to (highest close since entry) - trail_atr x ATR.
    #: None leaves it fixed, which is every result before 2026-09-22.
    trail_atr: float | None = None

    def __post_init__(self) -> None:
        if not self.use_stop and self.time_limit == 0:
            raise ValueError("a configuration with no stop needs a time limit")

    def resolved(self) -> RunConfig:
        """Apply per-hypothesis defaults from the specification.

        H1 (docs/03) exits on time or stop and has no profit target; the
        pattern hypotheses surface over R targets. One shared default would
        test something no specification describes.

        The holding period is resolved here for the same reason. H1 and H5
        both exit on `hold`, but they are not the same horizon: H1 is a
        short-term relative-strength rotation, H5 is momentum 12-1, whose
        literature and whose own `monthly_rebalance` flag both imply a month.
        A single shared default ran H5 on a five-day clock and measured the
        short-horizon momentum docs/03 records as much weaker.

        Idempotent: resolving an already-resolved config returns the same
        config. Callers resolve at more than one layer and must be able to,
        without the second pass reinterpreting the first pass's output.
        """
        hold = self.hold if self.hold is not None else HOLD_DEFAULTS[self.hypothesis]

        time_limit = self.time_limit
        if time_limit is None:
            if self.hypothesis in ("h1", "h5"):
                time_limit = hold
            elif self.hypothesis in ("h6", "h7"):
                time_limit = 20
            else:
                time_limit = 10
        # Two different things both look like "no target" here, and the
        # distinction decides the exit rule:
        #
        #   r_multiple is None  -- unspecified, so the hypothesis's own default
        #                          applies (h2-h4 surface over a 2R target).
        #   r_multiple <= 0     -- explicitly no target. A target at 0R sits on
        #                          the entry price, so ExitRule normalises it
        #                          to None at the engine boundary, which is
        #                          where "no target" has to mean something.
        #
        # "No target" canonicalises to 0.0 and NOT to None, because resolved()
        # has to be a FIXED POINT: battery.py resolves a config to key its
        # candidate cache, then evaluate() resolves again before running it.
        # Mapping 0 -> None made the second pass read that None as
        # "unspecified" and hand h2-h4 their 2R default, so six experiments
        # declaring no target ran WITH one -- h2/h3/h4 _no_stop and
        # _exit_isolated, logged as `r_multiple=None` while the engine used
        # 2.0. Distinguishable in a report only by target exits appearing in a
        # run that has no target. That is the third time this project has
        # recorded a configuration it did not run; test_resolved_is_idempotent
        # is what keeps it from being the fourth.
        #
        # Mirrored here rather than left to ExitRule because RunConfig is what
        # gets hashed for budget and written to config_json.
        r_multiple = self.r_multiple
        if r_multiple is not None and r_multiple <= 0:
            r_multiple = 0.0
        elif r_multiple is None and self.hypothesis in ("h2", "h3", "h4"):
            r_multiple = 2.0
        return RunConfig(**{
            **self.__dict__,
            "hold": hold,
            "time_limit": time_limit,
            "r_multiple": r_multiple,
        })

    def as_dict(self) -> dict[str, Any]:
        """Only the parameters this hypothesis actually reads.

        Irrelevant fields are dropped so the config hash -- which decides
        whether a run spends budget -- does not change when an unrelated
        default moves.
        """
        data = dict(self.__dict__)
        relevant = {
            "h1": ("stop_atr", "rs_lookback", "top_pct", "hold", "entry_delay"),
            "h5": ("stop_atr", "top_pct", "mom_lookback", "mom_skip", "monthly_rebalance"),
            "h6": ("stop_atr", "reaction_pct", "entry_delay"),
            "h7": ("squeeze_percentile", "squeeze_window", "breakout_window"),
            "h2": ("displacement",),
            "h3": ("sweep_lookback",),
        }
        keep = set(relevant.get(self.hypothesis, ()))
        for group in relevant.values():
            for key in group:
                if key not in keep:
                    data.pop(key, None)
        return data


@dataclass
class Outcome:
    config: RunConfig
    stats: Stats
    regimes: dict[str, Stats]
    candidates: int
    rejected: dict[str, int]
    # Rank against random symbols on random dates -- selection and timing together.
    random_percentile: float | None
    # Rank against random symbols on THIS strategy's own entry dates. Timing is
    # identical on both sides, so this one is about the pick. Quote this.
    date_matched_percentile: float | None = None
    # Mean per-trade fractional return and its standard error, in the same unit
    # as the benchmarks. The SE is clustered by entry month (inference.py):
    # concurrent positions in correlated names are not independent, and the
    # iid version overstated the evidence.
    mean_return: float | None = None
    mean_return_se: float | None = None
    # Every closed trade as (ticker, entry date, return). Kept so two arms that
    # took the same signals can be compared PAIRED -- same stock, same day,
    # different exit -- which is the test the exit-isolated arms exist for.
    trade_log: tuple = ()
    # One-sided p against random names on the same days: the number the
    # pre-registered vs-random criterion and the Holm correction read.
    same_day_p: float | None = None
    # Trades divided by the month-clustered design effect: how many independent
    # observations the run actually holds. The trade-count criterion reads this.
    effective_trades: float | None = None
    # Per regime bucket: return, and whether it beat random names on its days.
    regime_results: dict = field(default_factory=dict)
    criteria: list = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.criteria) and all(c.passed for c in self.criteria)


def load_symbol_bars(
    session: Session, symbols: str | None, *, splits_until: date | None = None
) -> dict[str, pd.DataFrame]:
    """Every symbol's bars, minus the ones we know are the wrong company.

    The quarantine is applied HERE as well as in `universe_members`, because
    those are two different doors into a run and most runs use only this one:
    `backtest run` and `research explore` default `--universe` to None, so
    every result in the project to date was computed over every symbol in the
    database. Filtering membership alone would have left BBBY's Overstock
    prices in every battery while the quarantine reported success.

    An explicitly named symbol is dropped too. A contaminated series is not
    more trustworthy for having been asked for by name.

    `splits_until` must be the last date the run may see. Without it a split
    years after the window changes trades inside it -- see `load_bars`.
    """
    stmt = select(Symbol).order_by(Symbol.ticker)
    if symbols:
        wanted = [t.strip().upper() for t in symbols.split(",") if t.strip()]
        stmt = stmt.where(Symbol.ticker.in_(wanted))
    rows = [(s.id, s.ticker) for s in session.scalars(stmt)]

    excluded = quarantine.symbols()
    dropped = sorted({ticker for _, ticker in rows} & excluded)
    if dropped:
        log.warning(
            "quarantine: %d symbol(s) excluded from this run -- %s. "
            "See data/reference/universe_quarantine.csv for the reason on each.",
            len(dropped), ", ".join(dropped),
        )

    # One query for every symbol's splits rather than one per symbol: a
    # thousand round trips for a table holding a few thousand rows.
    splits_by_symbol = load_splits_bulk(session)
    bars = {
        ticker: load_bars(
            session, sid,
            splits=splits_by_symbol.get(sid, []), splits_until=splits_until,
        )
        for sid, ticker in rows
        if ticker not in excluded
    }
    return {k: v for k, v in bars.items() if not v.empty}


def build_candidates(
    bars_by_symbol: dict[str, pd.DataFrame],
    config: RunConfig,
    universe=always_in_universe,
    events_by_symbol: dict[str, list] | None = None,
) -> list[Candidate]:
    """Signal generation. Depends only on the entry-side parameters, so a
    surface that varies exit rules can reuse one call across every cell."""
    trend = TrendFilter(enabled=config.trend_filter)
    if config.hypothesis == "h1":
        return relative_strength_candidates(
            bars_by_symbol, trend=trend, rebalance_days=config.hold,
            top_pct=config.top_pct, stop_atr=config.stop_atr,
            lookback=config.rs_lookback, universe=universe,
            entry_delay=config.entry_delay,
        )
    if config.hypothesis == "h5":
        return canonical_momentum_candidates(
            bars_by_symbol, lookback=config.mom_lookback, skip=config.mom_skip,
            top_pct=config.top_pct, stop_atr=config.stop_atr,
            monthly=config.monthly_rebalance, trend=trend, universe=universe,
        )
    if config.hypothesis == "h6":
        if not events_by_symbol:
            raise ValueError(
                "h6 needs earnings dates. Run 'screener ingest-earnings' first."
            )
        return drift_candidates(
            bars_by_symbol, events_by_symbol, reaction_pct=config.reaction_pct,
            entry_delay=config.entry_delay, stop_atr=config.stop_atr,
            trend=trend, universe=universe,
        )
    extra: dict[str, Any] = {}
    if config.hypothesis == "h2":
        extra["displacement_min"] = config.displacement
    if config.hypothesis == "h3":
        extra["n_bar"] = config.sweep_lookback
    if config.hypothesis == "h7":
        extra["percentile"] = config.squeeze_percentile
        extra["window"] = config.squeeze_window
        extra["breakout_window"] = config.breakout_window
    return pattern_candidates(
        bars_by_symbol, hypothesis=config.hypothesis, trend=trend,
        universe=universe, **extra,
    )


#: Spread tables are expensive -- Corwin-Schultz across every symbol -- and the
#: battery runs hundreds of configurations over the SAME bars. Keyed by a
#: fingerprint of the bar set rather than its identity, so a rebuilt dict with
#: the same content still hits.
_SPREAD_CACHE: dict[tuple, dict[str, pd.Series]] = {}


def _costs_for(config: RunConfig, bars_by_symbol: dict[str, pd.DataFrame]) -> CostModel:
    """The cost model for a run, with per-symbol spreads where measurable.

    Symbols too short to estimate fall back to `slippage_bps`, which is why
    that figure stays deliberately high rather than being lowered to match the
    mega caps it was calibrated on.
    """
    if not config.measured_spreads:
        return CostModel(slippage_bps=config.slippage_bps)
    key = (
        tuple(sorted(bars_by_symbol)),
        sum(len(f) for f in bars_by_symbol.values()),
    )
    table = _SPREAD_CACHE.get(key)
    if table is None:
        table = spread_table(bars_by_symbol)
        _SPREAD_CACHE[key] = table
    return CostModel(slippage_bps=config.slippage_bps, spreads=table)


def simulate(
    candidates: list[Candidate],
    bars_by_symbol: dict[str, pd.DataFrame],
    config: RunConfig,
    split: Split,
):
    """Execute one configuration and return the raw backtest, trades included.

    The one place a RunConfig becomes risk limits, an exit rule and a cost
    model. `evaluate` scores the result; diagnostics that need the individual
    trades -- effective sample size, paired arm comparisons -- call this rather
    than rebuilding the setup, so the two cannot drift apart.
    """
    config = config.resolved()
    return run_backtest(
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
            trail_atr=config.trail_atr,
        ),
        costs=_costs_for(config, bars_by_symbol),
    )


def evaluate(
    candidates: list[Candidate],
    bars_by_symbol: dict[str, pd.DataFrame],
    config: RunConfig,
    split: Split,
    *,
    random_iterations: int = 1000,
    seed: int = 0,
    alpha: float = FAMILY_WISE_ALPHA,
    universe=None,
) -> Outcome:
    """Run one configuration and score it against the pre-registered criteria."""
    result = simulate(candidates, bars_by_symbol, config, split)
    return score(
        result, bars_by_symbol, config, split, candidates=len(candidates),
        random_iterations=random_iterations, seed=seed, alpha=alpha,
        universe=universe,
    )


def score(
    result,
    bars_by_symbol: dict[str, pd.DataFrame],
    config: RunConfig,
    split: Split,
    *,
    candidates: int = 0,
    random_iterations: int = 1000,
    seed: int = 0,
    alpha: float = FAMILY_WISE_ALPHA,
    universe=None,
) -> Outcome:
    """Everything the pre-registered criteria read, computed in one place.

    `universe` is the SAME predicate the strategy was restricted by, and it
    must be passed whenever one was. The benchmarks otherwise draw from every
    stored symbol while the strategy draws from index members, and the
    percentile then answers a question nobody asked. See
    `benchmarks.date_matched_benchmark`.

    `screener backtest run`, the battery and every diagnostic score through
    here. Until 2026-09-19 the run command computed its own criteria beside
    this function, and the two had already drifted: one had the date-matched
    benchmark and clustered errors, the other did not.
    """
    config = config.resolved()
    costs = _costs_for(config, bars_by_symbol)
    stats = summarize(result)
    regime_stats = by_regime(result.trades, config.equity)

    log = tuple(
        (t.ticker, t.entry_date, r)
        for t in result.closed_trades
        if (r := trade_return(t)) is not None
    )
    mean_return = mean_return_se = effective = None
    if log:
        clustered = inference.sample(log)
        mean_return = clustered.mean
        if not math.isnan(clustered.se):
            mean_return_se = clustered.se
        if not math.isnan(clustered.effective_n):
            effective = clustered.effective_n

    percentile = date_matched = same_day_p = None
    regime_results: dict[str, RegimeResult] = {
        name: RegimeResult(name, s.trades, s.total_return_pct, None)
        for name, s in regime_stats.items()
    }
    holds = [t.bars_held for t in result.closed_trades if t.bars_held > 0]
    if holds and random_iterations > 0:
        observed = mean_return if mean_return is not None else 0.0
        bench = random_benchmark(
            bars_by_symbol, start=split.start, end=split.end,
            n_trades=len(holds), hold_periods=holds,
            iterations=random_iterations, seed=seed, costs=costs,
        )
        percentile = bench.percentile_of(observed)

        # Same trades, same days, different names. The gap between this and the
        # line above is how much of the rank was timing rather than selection.
        matched = date_matched_benchmark(
            bars_by_symbol, entries=trade_entries(result.closed_trades),
            iterations=random_iterations, seed=seed, costs=costs,
            eligible=universe,
        )
        if matched.distribution.size:
            date_matched = matched.percentile_of(observed)
            same_day_p = matched.p_value(observed)

        # The same question inside each regime: did the picks beat random
        # names bought on those days? Asks about selection in a falling market
        # rather than whether a long-only rule made money in one.
        for name, rstats in regime_stats.items():
            inside = [t for t in result.closed_trades
                      if regime_for(t.entry_date) == name and trade_return(t) is not None]
            if not inside:
                continue
            regime_mean = sum(trade_return(t) for t in inside) / len(inside)
            regime_bench = date_matched_benchmark(
                bars_by_symbol, entries=trade_entries(inside),
                iterations=random_iterations, seed=seed, costs=costs,
                eligible=universe,
            )
            regime_results[name] = RegimeResult(
                name, rstats.trades, rstats.total_return_pct,
                regime_bench.percentile_of(regime_mean)
                if regime_bench.distribution.size else None,
            )

    return Outcome(
        config=config,
        stats=stats,
        regimes=regime_stats,
        candidates=candidates,
        rejected=result.rejected,
        random_percentile=percentile,
        date_matched_percentile=date_matched,
        mean_return=mean_return,
        mean_return_se=mean_return_se,
        trade_log=log,
        same_day_p=same_day_p,
        effective_trades=effective,
        regime_results=regime_results,
        criteria=check_criteria(
            stats,
            effective_trades=effective,
            regimes=regime_results,
            regime_buckets_in_split=split_regime_count(split.start, split.end),
            same_day_p=same_day_p,
            alpha=alpha,
        ),
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


def _entry_key(config: RunConfig) -> tuple:
    """Identity of the signal-generation inputs.

    Cells sharing this key share one generation pass, so an exit-only surface
    generates signals once rather than once per cell. Every entry-side field
    must appear here -- omitting one would silently reuse the wrong signals.
    """
    return (
        config.hypothesis, config.trend_filter, config.displacement,
        config.hold, config.top_pct, config.stop_atr, config.rs_lookback,
        config.sweep_lookback, config.mom_lookback, config.mom_skip,
        config.monthly_rebalance, config.reaction_pct, config.entry_delay,
        config.squeeze_percentile, config.squeeze_window, config.breakout_window,
    )
