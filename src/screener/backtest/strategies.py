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

from ..calc.indicators import atr, slope_positive, sma
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
        out.append(
            Candidate(
                ticker=ticker,
                setup=event.setup,
                signal_date=signal_day,
                entry_date=entry_day,
                stop_level=event.stop_level,
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
            _events_to_candidates(ticker, bars, events, universe, sectors.get(ticker))
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
            # Stop is set from the entry bar's OPEN, which is not yet known at
            # ranking time -- so it is expressed relative to the last close and
            # the engine treats it as an absolute level.
            reference_close = float(bars["close"].loc[day])
            candidates.append(
                Candidate(
                    ticker=ticker,
                    setup="rs_continuation",
                    signal_date=day.date(),
                    entry_date=entry_day,
                    stop_level=reference_close - stop_atr * float(atr_value),
                    rank=rank_value,
                    sector=sectors.get(ticker),
                )
            )
    return sorted(candidates, key=lambda c: (c.entry_date, -c.rank, c.ticker))
