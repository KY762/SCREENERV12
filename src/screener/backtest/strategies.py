"""Hypothesis -> candidate translation.

Each function turns stored bars into ``Candidate`` objects for the engine. They
own no arithmetic: geometry comes from ``calc.patterns``, trend and ranking from
``calc.indicators`` and ``calc.relative_strength``. Reimplementing any of it
here would put the golden-value and no-lookahead tests out of reach of the code
that actually decides trades.

The universe mask is applied per DATE, not per symbol. A symbol that qualifies
today did not necessarily qualify in 2013, and screening history against today's
list is how a backtest quietly restricts itself to companies that survived.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date

import pandas as pd

from ..calc.compression import expansion_events
from ..calc.indicators import atr, slope_positive, sma
from ..calc.momentum import month_end_mask, volatility_scaled_momentum
from ..calc.patterns import fvg_entry_events, ifvg_entry_events, sweep_entry_events
from ..calc.relative_strength import relative_strength_adjusted
from .engine import Candidate

# A predicate answering "was this ticker in the universe on this date?"
UniverseMask = Callable[[str, date], bool]


def always_in_universe(ticker: str, day: date) -> bool:
    return True


@dataclass(frozen=True)
class TrendFilter:
    """The shared trend condition (docs/03 H1 conditions).

    ``enabled=False`` is a real configuration, not a debugging convenience --
    whether the trend filter contributes anything is one of the structural
    questions the development split exists to answer.
    """

    enabled: bool = True
    fast: int = 50
    slow: int = 200
    slope_lookback: int = 21

    def mask(self, bars: pd.DataFrame) -> pd.Series | None:
        if not self.enabled:
            return None
        close = bars["close"]
        fast_ma = sma(close, self.fast)
        slow_ma = sma(close, self.slow)
        rising = slope_positive(slow_ma, self.slope_lookback)
        return (close > fast_ma) & (fast_ma > slow_ma) & rising


def _events_to_candidates(
    ticker: str,
    bars: pd.DataFrame,
    events,
    universe: UniverseMask,
    sector: str | None,
    atr_series: pd.Series | None = None,
) -> list[Candidate]:
    out: list[Candidate] = []
    index = bars.index
    for event in events:
        if event.entry_idx >= len(index):
            continue
        signal_day = index[event.trigger_idx].date()
        entry_day = index[event.entry_idx].date()
        if not universe(ticker, entry_day):
            continue
        atr_value = None
        if atr_series is not None:
            raw = atr_series.iloc[event.trigger_idx]
            atr_value = None if pd.isna(raw) else float(raw)
        out.append(
            Candidate(
                ticker=ticker,
                setup=event.setup,
                signal_date=signal_day,
                entry_date=entry_day,
                # The stop is the setup's geometry -- the gap edge, the sweep
                # low -- so it stays an absolute level.
                stop_level=event.stop_level,
                atr=atr_value,
                sector=sector,
            )
        )
    return out


def pattern_candidates(
    bars_by_symbol: Mapping[str, pd.DataFrame],
    *,
    hypothesis: str,
    trend: TrendFilter | None = None,
    universe: UniverseMask = always_in_universe,
    sectors: Mapping[str, str] | None = None,
    **kwargs,
) -> list[Candidate]:
    """Candidates for H2 (fvg), H3 (sweep) or H4 (ifvg).

    ``kwargs`` pass straight through to the detector, so a parameter surface is
    swept by calling this repeatedly rather than by editing anything.
    """
    detectors = {
        "h2": fvg_entry_events,
        "fvg": fvg_entry_events,
        "h3": sweep_entry_events,
        "sweep": sweep_entry_events,
        "h4": ifvg_entry_events,
        "ifvg": ifvg_entry_events,
        "h7": expansion_events,
        "squeeze": expansion_events,
    }
    key = hypothesis.strip().lower()
    if key not in detectors:
        raise ValueError(
            f"unknown hypothesis {hypothesis!r}; expected one of {', '.join(sorted(detectors))}"
        )
    detector = detectors[key]
    trend = trend if trend is not None else TrendFilter()
    sectors = sectors or {}

    candidates: list[Candidate] = []
    for ticker, bars in bars_by_symbol.items():
        if bars.empty:
            continue
        events = detector(bars, trend_mask=trend.mask(bars), **kwargs)
        candidates.extend(
            _events_to_candidates(
                ticker, bars, events, universe, sectors.get(ticker), atr(bars, 14)
            )
        )
    return sorted(candidates, key=lambda c: (c.entry_date, c.ticker))


def relative_strength_candidates(
    bars_by_symbol: Mapping[str, pd.DataFrame],
    *,
    benchmark: str = "SPY",
    lookback: int = 63,
    top_pct: float = 0.10,
    stop_atr: float = 2.0,
    atr_window: int = 14,
    trend: TrendFilter | None = None,
    rebalance_days: int = 5,
    universe: UniverseMask = always_in_universe,
    sectors: Mapping[str, str] | None = None,
) -> list[Candidate]:
    """H1 -- the control. Rank by volatility-adjusted RS, take the top slice.

    Ranking happens across the cross-section as of each rebalance date using
    only that date's values, and execution is the next session's open. This is
    the hypothesis every other one has to beat; if it cannot be beaten, the
    added complexity earned nothing.
    """
    trend = trend if trend is not None else TrendFilter()
    sectors = sectors or {}
    benchmark_bars = bars_by_symbol.get(benchmark)
    if benchmark_bars is None or benchmark_bars.empty:
        raise ValueError(f"benchmark {benchmark} has no bars; ingest it first")

    rs_by_symbol: dict[str, pd.Series] = {}
    trend_by_symbol: dict[str, pd.Series | None] = {}
    atr_by_symbol: dict[str, pd.Series] = {}
    for ticker, bars in bars_by_symbol.items():
        if ticker == benchmark or bars.empty:
            continue
        rs_by_symbol[ticker] = relative_strength_adjusted(
            bars["close"], benchmark_bars["close"], lookback
        )
        mask = trend.mask(bars)
        # NaN during warmup means "not known to be in an uptrend", which is a
        # rejection. Coercing here keeps the ambiguity out of the hot loop.
        trend_by_symbol[ticker] = None if mask is None else mask.fillna(False).astype(bool)
        atr_by_symbol[ticker] = atr(bars, atr_window)

    if not rs_by_symbol:
        return []

    calendar = sorted({day for s in rs_by_symbol.values() for day in s.index})
    candidates: list[Candidate] = []

    for i in range(0, len(calendar) - 1, max(rebalance_days, 1)):
        day = calendar[i]
        scored: list[tuple[float, str]] = []
        for ticker, series in rs_by_symbol.items():
            if day not in series.index:
                continue
            value = series.loc[day]
            if pd.isna(value):
                continue
            trend_series = trend_by_symbol[ticker]
            if trend_series is not None:
                if day not in trend_series.index or not bool(trend_series.loc[day]):
                    continue
            scored.append((float(value), ticker))

        if not scored:
            continue
        scored.sort(reverse=True)
        take = max(1, int(len(scored) * top_pct))

        for rank_value, ticker in scored[:take]:
            bars = bars_by_symbol[ticker]
            position = bars.index.get_indexer([day])[0]
            if position < 0 or position + 1 >= len(bars.index):
                continue
            atr_value = atr_by_symbol[ticker].loc[day]
            if pd.isna(atr_value) or atr_value <= 0:
                continue
            entry_day = bars.index[position + 1].date()
            if not universe(ticker, entry_day):
                continue
            # docs/03 H1: "Stop at entry - k x ATR(14)". A DISTANCE, not a
            # level. Anchoring it to the last known close instead would let the
            # overnight gap decide how much is risked -- and on a gap down to
            # just above the level, risk per share collapses and an ordinary
            # day's move reads as a loss of many R.
            candidates.append(
                Candidate(
                    ticker=ticker,
                    setup="rs_continuation",
                    signal_date=day.date(),
                    entry_date=entry_day,
                    stop_distance=stop_atr * float(atr_value),
                    atr=float(atr_value),
                    rank=rank_value,
                    sector=sectors.get(ticker),
                )
            )
    return sorted(candidates, key=lambda c: (c.entry_date, -c.rank, c.ticker))


# --------------------------------------------------------------------------
# Round 2
# --------------------------------------------------------------------------

def canonical_momentum_candidates(
    bars_by_symbol: Mapping[str, pd.DataFrame],
    *,
    lookback: int = 252,
    skip: int = 21,
    top_pct: float = 0.10,
    stop_atr: float = 3.0,
    atr_window: int = 14,
    vol_window: int = 63,
    monthly: bool = True,
    trend: TrendFilter | None = None,
    universe: UniverseMask = always_in_universe,
    sectors: Mapping[str, str] | None = None,
) -> list[Candidate]:
    """H5 -- cross-sectional momentum in its canonical form.

    Round 1's H1 ranked on a 63-day return, rebalanced every 5 days, with a
    2-ATR stop. Every one of those choices departs from the effect the
    literature documents, and all of them failed together, so which departure
    mattered is unknown. This is the version with the replication behind it:

        12-month formation, skipping the most recent month, monthly rebalance.

    The skip is the substantive difference. Short-horizon returns reverse, so a
    63-day lookback with no skip mixes reversal into continuation. The monthly
    rebalance is equally substantive: the anomaly is documented at monthly
    frequency, and rebalancing weekly changes the effect and multiplies costs.

    The stop stays wide by default and is expressed as a distance, because the
    strongest Round 1 finding was that a stop set inside normal noise costs
    more than it protects.
    """
    trend = trend if trend is not None else TrendFilter(enabled=False)
    sectors = sectors or {}

    scores: dict[str, pd.Series] = {}
    trends: dict[str, pd.Series | None] = {}
    atrs: dict[str, pd.Series] = {}
    for ticker, bars in bars_by_symbol.items():
        if bars.empty or len(bars) < lookback + 5:
            continue
        scores[ticker] = volatility_scaled_momentum(
            bars["close"], lookback, skip, vol_window
        )
        mask = trend.mask(bars)
        trends[ticker] = None if mask is None else mask.fillna(False).astype(bool)
        atrs[ticker] = atr(bars, atr_window)

    if not scores:
        return []

    calendar = sorted({day for s in scores.values() for day in s.index})
    if monthly:
        marks = month_end_mask(pd.DatetimeIndex(calendar))
        rebalance_days = [d for d, flag in zip(calendar, marks, strict=True) if flag]
    else:
        rebalance_days = calendar

    candidates: list[Candidate] = []
    for day in rebalance_days:
        ranked: list[tuple[float, str]] = []
        for ticker, series in scores.items():
            if day not in series.index:
                continue
            value = series.loc[day]
            if pd.isna(value):
                continue
            trend_series = trends[ticker]
            if trend_series is not None and (
                day not in trend_series.index or not bool(trend_series.loc[day])
            ):
                continue
            ranked.append((float(value), ticker))

        if not ranked:
            continue
        ranked.sort(reverse=True)
        for score, ticker in ranked[: max(1, int(len(ranked) * top_pct))]:
            bars = bars_by_symbol[ticker]
            position = bars.index.get_indexer([day])[0]
            if position < 0 or position + 1 >= len(bars.index):
                continue
            atr_value = atrs[ticker].loc[day]
            if pd.isna(atr_value) or atr_value <= 0:
                continue
            entry_day = bars.index[position + 1].date()
            if not universe(ticker, entry_day):
                continue
            candidates.append(
                Candidate(
                    ticker=ticker,
                    setup="momentum_12_1",
                    signal_date=day.date(),
                    entry_date=entry_day,
                    stop_distance=stop_atr * float(atr_value),
                    atr=float(atr_value),
                    rank=score,
                    sector=sectors.get(ticker),
                )
            )
    return sorted(candidates, key=lambda c: (c.entry_date, -c.rank, c.ticker))


def drift_candidates(
    bars_by_symbol: Mapping[str, pd.DataFrame],
    events_by_symbol: Mapping[str, list],
    *,
    reaction_pct: float = 0.03,
    entry_delay: int = 1,
    stop_atr: float = 3.0,
    atr_window: int = 14,
    trend: TrendFilter | None = None,
    universe: UniverseMask = always_in_universe,
    sectors: Mapping[str, str] | None = None,
) -> list[Candidate]:
    """H6 -- post-earnings drift, anchored on the reported reaction.

    The literature's version sorts on earnings SURPRISE against analyst
    estimates. We have no estimates and no budget for them, so this sorts on
    the market's own reaction instead: a filing date, and a move of at least
    ``reaction_pct`` on it.

    That substitution is a real weakening and is stated wherever the results
    are. Price reaction conflates the surprise with how the surprise was
    received, and the filing date lags the press release. Both push toward
    finding nothing, which is the safe direction to be wrong in -- but a null
    result here is weaker evidence against drift than a null in the literature's
    setup would be.
    """
    trend = trend if trend is not None else TrendFilter(enabled=False)
    sectors = sectors or {}
    candidates: list[Candidate] = []

    for ticker, bars in bars_by_symbol.items():
        events = events_by_symbol.get(ticker) or []
        if bars.empty or not events:
            continue
        atr_series = atr(bars, atr_window)
        mask = trend.mask(bars)
        trend_series = None if mask is None else mask.fillna(False).astype(bool)
        close = bars["close"]

        for event_date in events:
            stamp = pd.Timestamp(event_date)
            position = bars.index.searchsorted(stamp)
            if position <= 0 or position + entry_delay >= len(bars.index):
                continue
            day = bars.index[position]
            reaction = (close.iloc[position] - close.iloc[position - 1]) / close.iloc[position - 1]
            if reaction < reaction_pct:
                continue
            if trend_series is not None and not bool(trend_series.iloc[position]):
                continue
            atr_value = atr_series.iloc[position]
            if pd.isna(atr_value) or atr_value <= 0:
                continue
            entry_day = bars.index[position + entry_delay].date()
            if not universe(ticker, entry_day):
                continue
            candidates.append(
                Candidate(
                    ticker=ticker,
                    setup="earnings_drift",
                    signal_date=day.date(),
                    entry_date=entry_day,
                    stop_distance=stop_atr * float(atr_value),
                    atr=float(atr_value),
                    rank=float(reaction),
                    sector=sectors.get(ticker),
                )
            )
    return sorted(candidates, key=lambda c: (c.entry_date, -c.rank, c.ticker))
