"""Does an indicator predict anything, before any strategy is built on it?

Every battery in this project tests a STRATEGY: an indicator, plus a holding
period, plus a stop, plus position sizing, plus portfolio limits. When such a
thing fails there is no way to tell which part failed. Four rounds and 588
configurations were spent that way.

This asks the prior question directly. Rank every symbol by the indicator on a
date, rank the same symbols by what they went on to return, and correlate the
two rankings. That number -- the information coefficient -- is the indicator's
predictive content, with no exit rule, no stop and no portfolio in the way.

    IC near zero      the indicator carries no cross-sectional signal at this
                      horizon on this universe. No configuration built on it
                      can work, and sweeping holds and stops is wasted effort.
    IC around 0.02-0.05 with a t-statistic above 3 is a real and ordinary
                      equity factor. Published anomalies mostly live here.
    IC above 0.10     implausible on liquid large caps. Suspect lookahead
                      before celebrating.

WHY RANKS RATHER THAN VALUES. A Spearman correlation is unaffected by outliers
and by the indicator's scale, so a single 262x fake return of the kind the
quarantine was built to remove cannot dominate the estimate. It also matches
how the strategies actually use these indicators: every one of them ranks and
takes a top slice, none reads the level.

WHAT THIS STILL DOES NOT TELL YOU. An indicator with real IC can still lose
money after costs, and one with no IC in the top decile can carry signal in the
tails. This measures the average monotonic relationship across the whole
cross-section, which is the thing a ranking rule depends on.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from math import sqrt

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

#: Fewer names than this on a date and the rank correlation is noise.
MIN_NAMES = 20


@dataclass(frozen=True)
class ICResult:
    """One indicator at one horizon."""

    indicator: str
    horizon: int
    dates: int
    mean_names: float
    mean_ic: float
    std_ic: float
    hit_rate: float          # fraction of dates with IC > 0

    @property
    def t_stat(self) -> float:
        """How many standard errors the mean IC sits from zero.

        Dates are treated as independent observations, which overstates
        confidence: overlapping forward windows share returns, so a 20-day
        horizon sampled daily counts each move about 20 times. `stride` in
        `information_coefficient` is how that is controlled -- sample every
        `horizon` sessions and the windows stop overlapping.
        """
        if self.dates < 2 or self.std_ic == 0:
            return 0.0
        return self.mean_ic / (self.std_ic / sqrt(self.dates))

    def verdict(self) -> str:
        if self.dates < 2:
            return "not enough dates"
        t = abs(self.t_stat)
        if t < 2:
            return "no detectable signal"
        if abs(self.mean_ic) < 0.01:
            return "detectable but tiny"
        if abs(self.mean_ic) > 0.10:
            return "implausibly strong -- check for lookahead"
        return "real, ordinary factor strength"

    def describe(self) -> str:
        return (
            f"{self.indicator} @ {self.horizon}d: IC {self.mean_ic:+.4f} "
            f"t={self.t_stat:+.2f} over {self.dates} date(s), "
            f"{self.hit_rate:.0%} positive -- {self.verdict()}"
        )


def forward_returns(
    bars_by_symbol: dict[str, pd.DataFrame], horizon: int
) -> dict[str, pd.Series]:
    """Return from the NEXT open to the open `horizon` sessions later.

    Open to open, not close to close, because that is what this platform can
    actually capture: a signal completes at a bar's close and fills at the next
    bar's open (non-negotiable 1). Measuring close-to-close from the signal bar
    would credit the indicator with the overnight move it could not have
    traded, which is the most common way an IC is quietly inflated.

    The series is indexed by SIGNAL date, so it lines up with the indicator
    without any further shifting at the call site.
    """
    out: dict[str, pd.Series] = {}
    for ticker, bars in bars_by_symbol.items():
        if len(bars) < horizon + 2 or "open" not in bars:
            continue
        opens = bars["open"].to_numpy(dtype="float64")
        entry = opens[1:]                       # fill on the session after the signal
        exit_ = opens[1 + horizon:]
        n = len(exit_)
        if n <= 0:
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            rets = np.where(entry[:n] > 0, exit_ / entry[:n] - 1.0, np.nan)
        out[ticker] = pd.Series(rets, index=bars.index[:n])
    return out


def information_coefficient(
    values_by_symbol: dict[str, pd.Series],
    bars_by_symbol: dict[str, pd.DataFrame],
    *,
    indicator: str,
    horizon: int,
    start: date,
    end: date,
    universe: Callable[[str, date], bool] | None = None,
    stride: int | None = None,
) -> ICResult:
    """Rank correlation between an indicator and what followed it.

    `stride` controls overlap. Sampling every session with a 20-day horizon
    reuses each forward window 20 times, which makes the t-statistic far too
    confident; the default samples every `horizon` sessions so the windows are
    disjoint. Pass 1 deliberately if the point is the IC itself rather than its
    significance.

    `universe` must be the same membership the strategy would be restricted by.
    An indicator can carry signal across all listed names and none within the
    S&P 500, and it is the second that decides whether a rule here can work.
    """
    forwards = forward_returns(bars_by_symbol, horizon)
    step = stride if stride is not None else max(1, horizon)

    calendar = sorted({
        stamp for series in values_by_symbol.values() for stamp in series.index
    })
    calendar = [
        stamp for stamp in calendar
        if start <= stamp.date() <= end
    ][::step]

    ics: list[float] = []
    counts: list[int] = []
    for stamp in calendar:
        day = stamp.date()
        signal: list[float] = []
        future: list[float] = []
        for ticker, series in values_by_symbol.items():
            if universe is not None and not universe(ticker, day):
                continue
            if stamp not in series.index:
                continue
            value = series.loc[stamp]
            forward = forwards.get(ticker)
            if forward is None or stamp not in forward.index:
                continue
            outcome = forward.loc[stamp]
            if pd.isna(value) or pd.isna(outcome):
                continue
            signal.append(float(value))
            future.append(float(outcome))

        if len(signal) < MIN_NAMES:
            continue
        # Spearman: rank both sides, then correlate. Immune to the indicator's
        # scale and to a single extreme return dominating the estimate.
        sr = pd.Series(signal).rank()
        fr = pd.Series(future).rank()
        if sr.std() == 0 or fr.std() == 0:
            continue
        ics.append(float(sr.corr(fr)))
        counts.append(len(signal))

    if not ics:
        return ICResult(indicator, horizon, 0, 0.0, 0.0, 0.0, 0.0)

    arr = np.asarray(ics, dtype="float64")
    return ICResult(
        indicator=indicator,
        horizon=horizon,
        dates=len(arr),
        mean_names=float(np.mean(counts)),
        mean_ic=float(arr.mean()),
        std_ic=float(arr.std(ddof=1)) if len(arr) > 1 else 0.0,
        hit_rate=float((arr > 0).mean()),
    )
