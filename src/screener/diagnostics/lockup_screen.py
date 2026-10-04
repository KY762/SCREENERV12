"""H9, the IPO lock-up expiry screen: do names underperform in the trading
days right after their lock-up expires?

Field & Hanka (2001), 1,948 lock-up expirations, 1988-1997: roughly -1.5%
abnormal return over the three trading days around expiry, trading volume
up about 40% permanently afterward, the effect larger for VC-backed firms.
Loughran & Ritter (1995), 4,753 US IPOs, 1970-1990: underperformance over a
longer, 5-year horizon. This module tests the shorter, sharper Field &
Hanka effect, which is the one a signal with a stated N-day window can
actually be pre-registered against -- see ``preregistrations/H9.md`` and
``docs/12-IPO-LOCKUP-SCREEN.md``.

Shaped on ``diagnostics/screen.py`` (H8, the avoid screen) deliberately:
same no-strategy, no-parameter-to-tune design -- there is a group of
dates picked by the lock-up calendar rather than a trading rule, and the
question is whether that group's mean return differs from a same-day
pool, after costs. ``trade_return`` is H8's own function, imported
unchanged: entry at the next session's open, refused on a zero-volume
bar, exit at the open ``horizon`` sessions later, a zero-volume bar's
open, or a series' last close. That is non-negotiable 1 (signals complete
at a bar's close, fill at the NEXT bar's open) applied to "the lock-up
expired on day E" as the signal.

WHAT THE POOL IS, AND WHY IT DIFFERS FROM H8'S. H8 compares against
``swing_small_mid``, a filtered point-in-time pool. H9's events are drawn
from this project's full stored equity universe (see
``ingest/lockups.py``), because a stock fresh off its IPO frequently has
not yet accumulated the trading history or dollar volume ``swing_small_
mid`` requires -- filtering the comparison pool to it but not the events
would compare an unfiltered group against a filtered one. The pool here
is therefore the same full equity universe the events were drawn from, on
the same calendar days. This is a real, stated difference from H8's
methodology, not an oversight.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import erfc, sqrt

import numpy as np
import pandas as pd

from ..backtest.splits import REGIMES, Split
from .screen import trade_return

#: Field & Hanka's own event window: a three-trading-day abnormal return
#: around lock-up expiry. The pre-registered, bar-tested horizon.
PRIMARY_HORIZON_DAYS = 3


@dataclass(frozen=True)
class EventOutcome:
    ticker: str
    expiry_date: date
    entry_date: date
    gross: float
    net: float
    pool_gross: float
    pool_net: float
    pool_n: int


def _entry_index(bars: pd.DataFrame, expiry: date) -> int | None:
    """Index of the bar ON or immediately BEFORE ``expiry`` -- the signal
    bar whose close completes the event, per non-negotiable 1. ``None`` if
    the series has no bar on or before that date, or nothing after it to
    enter on.
    """
    positions = bars.index.searchsorted(pd.Timestamp(expiry), side="right") - 1
    if positions < 0 or positions + 1 >= len(bars):
        return None
    return int(positions)


def measure(
    bars_by_symbol: dict[str, pd.DataFrame],
    events: list[tuple[str, date]],
    *,
    spreads: dict[str, pd.Series],
    horizon: int = PRIMARY_HORIZON_DAYS,
) -> list[EventOutcome]:
    """One ``EventOutcome`` per event whose ticker and expiry date resolve
    to an actual entry bar in ``bars_by_symbol``.

    An event whose ticker is not in ``bars_by_symbol`` (quarantined, or
    outside whatever symbol filter the caller applied), or whose expiry
    falls after the series' own last bar minus ``horizon``, is silently
    absent from the result -- the caller is expected to report how many
    confirmed events went in and how many outcomes came out, per CHARTER
    section 7.
    """
    resolved: dict[tuple[str, date], tuple[int, pd.Timestamp]] = {}
    for ticker, expiry in events:
        bars = bars_by_symbol.get(ticker)
        if bars is None or bars.empty:
            continue
        i = _entry_index(bars, expiry)
        if i is None:
            continue
        resolved[(ticker, expiry)] = (i, bars.index[i + 1])

    wanted_dates = {entry_ts for _, entry_ts in resolved.values()}

    # One pass over the whole universe, bucketing by the SAME entry dates
    # the events themselves use -- H8's own `measure` does the equivalent
    # pass over a strided calendar; this does it over the event calendar.
    pool: dict[pd.Timestamp, list[tuple[float, float]]] = {d: [] for d in wanted_dates}
    for ticker, bars in bars_by_symbol.items():
        if bars.empty:
            continue
        spread = spreads.get(ticker)
        idx = bars.index.isin(wanted_dates)
        if not idx.any():
            continue
        for i in np.flatnonzero(idx):
            stamp = bars.index[i]
            ret = trade_return(bars, int(i), horizon)
            if ret is None:
                continue
            cost = float(spread.get(stamp, np.nan)) if spread is not None else float("nan")
            pool[stamp].append((ret, cost))

    # (mean gross, mean net, n, the date's own median cost -- the same
    # fallback value used inside the pool, kept so an event missing its
    # own spread estimate is charged the identical fallback rather than a
    # second, independently-derived number).
    pool_stats: dict[pd.Timestamp, tuple[float, float, int, float]] = {}
    for stamp, rows in pool.items():
        if not rows:
            continue
        arr = np.asarray(rows, dtype="float64")
        gross, cost = arr[:, 0], arr[:, 1]
        median_cost = float(np.nanmedian(cost)) if not np.isnan(cost).all() else 0.0
        cost = np.where(np.isnan(cost), median_cost, cost)
        net = gross - cost
        pool_stats[stamp] = (float(gross.mean()), float(net.mean()), len(rows), median_cost)

    out: list[EventOutcome] = []
    for (ticker, expiry), (i, entry_ts) in resolved.items():
        bars = bars_by_symbol[ticker]
        gross = trade_return(bars, i, horizon)
        if gross is None or entry_ts not in pool_stats:
            continue
        spread = spreads.get(ticker)
        cost_val = float(spread.get(entry_ts, np.nan)) if spread is not None else float("nan")
        pool_gross, pool_net, pool_n, median_cost = pool_stats[entry_ts]
        if np.isnan(cost_val):
            cost_val = median_cost
        net = gross - max(cost_val, 0.0)
        out.append(EventOutcome(
            ticker=ticker, expiry_date=expiry, entry_date=entry_ts.date(),
            gross=gross, net=net, pool_gross=pool_gross, pool_net=pool_net, pool_n=pool_n,
        ))
    return out


def _trimmed(x: np.ndarray, cut: float = 0.10) -> float:
    x = np.sort(x)
    k = int(len(x) * cut)
    return float(x[k:len(x) - k].mean()) if len(x) > 10 else float("nan")


def _t(x: np.ndarray) -> float:
    return float(x.mean() / (x.std(ddof=1) / sqrt(len(x)))) if len(x) > 2 else float("nan")


@dataclass(frozen=True)
class Verdict:
    events: int
    mean_net_gap: float
    t_net: float
    p_net_one_sided: float
    mean_gross_gap: float
    t_gross: float
    mean_trimmed_gap: float
    regimes_negative: int
    regimes_total: int
    by_regime: dict[str, tuple[int, float]]

    @property
    def passes_development(self) -> bool:
        """docs/12 section 4: net gap one-sided p <= 0.05 in the
        UNDERPERFORMANCE direction, negative in >= 2 of the split's regime
        buckets, and the trimmed version negative too."""
        return (
            self.p_net_one_sided <= 0.05
            and self.regimes_negative >= 2
            and self.mean_trimmed_gap < 0
        )


def judge(outcomes: list[EventOutcome], split: Split) -> Verdict:
    """One-sided test of UNDERPERFORMANCE: event return minus the same-day
    pool's, with a negative mean read as evidence for the hypothesis.
    ``p_net_one_sided`` is therefore P(T <= observed t) under the null of
    no difference, not H8's P(T >= t) -- H8 tests for outperformance, this
    tests for the opposite sign, and a two-line difference here is cheaper
    than a wrong sign silently halving every p-value.
    """
    net_gap = np.array([o.net - o.pool_net for o in outcomes])
    gross_gap = np.array([o.gross - o.pool_gross for o in outcomes])
    trimmed_gap = np.array([o.net - o.pool_net for o in outcomes])
    t_net = _t(net_gap)
    by_regime: dict[str, tuple[int, float]] = {}
    for regime in REGIMES:
        if not (split.start <= regime.start <= split.end):
            continue
        sel = np.array([
            o.net - o.pool_net for o in outcomes
            if regime.start <= o.entry_date <= regime.end
        ])
        by_regime[regime.name] = (len(sel), float(sel.mean()) if len(sel) else float("nan"))
    negative = sum(1 for n, m in by_regime.values() if n and m < 0)
    return Verdict(
        events=len(net_gap), mean_net_gap=float(net_gap.mean()), t_net=t_net,
        p_net_one_sided=0.5 * erfc(-t_net / sqrt(2)),
        mean_gross_gap=float(gross_gap.mean()), t_gross=_t(gross_gap),
        mean_trimmed_gap=_trimmed(trimmed_gap),
        regimes_negative=negative, regimes_total=len(by_regime), by_regime=by_regime,
    )
