"""How exposed each hypothesis is to the population the data is missing.

The universe is today's large caps. `screener universe coverage` (2026-08-26)
found acquisitions 6/6 present and failures 0/6 present, so the history keeps
every good ending and loses every bad one. That bias sits on every result here,
but it is not equally large for every hypothesis, and a blanket caveat hides the
difference.

A company on its way to failing usually spends its last months falling. A rule
that buys recent losers -- mean reversion, value, distress -- would have bought
it had it been present, and its backtest is missing exactly those losses. A rule
that buys recent winners would rarely have touched it.

That makes the exposure estimable WITHOUT the missing data: rank every
candidate's trailing return against the cross-section on its signal date and
ask how often the rule buys the bottom decile. Random selection puts 10% there.

This is an inference, and it bounds one failure mode rather than all of them:

  - It sees the slow decline, which trailing return registers in advance.
  - It does not see the sudden collapse -- a fraud revealed, a trial failed, a
    run on deposits -- where the stock was unremarkable until it was gone. Any
    rule is exposed to those roughly in proportion to how many names it holds.
  - The bottom decile here is the bottom decile of SURVIVORS. With the failures
    absent the true cutoff sits lower, so these shares somewhat overstate how
    much of the real bottom decile a rule reaches.

It is evidence for the question "could this hypothesis be validated before
delisted coverage is fixed", not an answer to it. That call is the operator's.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

# Random selection lands in any one decile this often.
RANDOM_DECILE_SHARE = 0.10


@dataclass(frozen=True)
class Exposure:
    """One hypothesis's tilt toward recent losers, at one lookback."""

    hypothesis: str
    lookback: int
    candidates: int         # signals the rule fired inside the window
    ranked: int             # of those, how many had a trailing return to rank
    bottom_decile: float    # share of ranked candidates in decile 1
    bottom_quintile: float  # share in deciles 1-2
    top_decile: float       # share in decile 10, for contrast
    median_decile: float

    @property
    def unranked(self) -> int:
        return self.candidates - self.ranked

    @property
    def relative_to_random(self) -> float:
        """Bottom-decile share as a multiple of what random selection gets.

        Reported as a ratio rather than bucketed into "safe" / "exposed",
        because any cutoff here would be a threshold chosen after seeing the
        numbers.
        """
        return self.bottom_decile / RANDOM_DECILE_SHARE


def trailing_return_deciles(
    bars_by_symbol: dict[str, pd.DataFrame], lookback: int
) -> pd.DataFrame:
    """Decile 1-10 of every symbol's trailing return on every date.

    Decile 1 is the worst performers that day. Ranked only among symbols that
    have a value on that date, so a name that is not yet listed neither takes
    a decile nor shifts anyone else's.

    Uses closes up to and including the date, which is what a signal that
    completes at that bar's close could know. Nothing after it.
    """
    if lookback <= 0:
        raise ValueError("lookback must be positive")
    closes = pd.DataFrame(
        {ticker: frame["close"].astype("float64") for ticker, frame in bars_by_symbol.items()}
    ).sort_index()
    trailing = closes / closes.shift(lookback) - 1.0
    pct = trailing.rank(axis=1, pct=True, method="average")
    return np.ceil(pct * 10.0).clip(lower=1.0, upper=10.0)


def measure(
    hypothesis: str,
    candidates: Iterable,
    deciles: pd.DataFrame,
    *,
    lookback: int,
    start: date,
    end: date,
) -> Exposure:
    """Where on the trailing-return ladder this hypothesis's signals land.

    Only candidates whose signal falls inside [start, end] count, so the
    measurement covers the same window the results do. A candidate with no
    trailing return that day (too little history) is counted as unranked, NOT
    placed in the bottom decile -- that would invent distress.
    """
    in_window = [c for c in candidates if start <= c.signal_date <= end]
    found: list[int] = []
    for candidate in in_window:
        try:
            value = deciles.at[pd.Timestamp(candidate.signal_date), candidate.ticker]
        except KeyError:
            continue
        if value is None or (isinstance(value, float) and math.isnan(value)):
            continue
        found.append(int(value))

    if not found:
        return Exposure(hypothesis, lookback, len(in_window), 0,
                        float("nan"), float("nan"), float("nan"), float("nan"))

    arr = np.asarray(found)
    return Exposure(
        hypothesis=hypothesis,
        lookback=lookback,
        candidates=len(in_window),
        ranked=len(found),
        bottom_decile=float((arr == 1).mean()),
        bottom_quintile=float((arr <= 2).mean()),
        top_decile=float((arr == 10).mean()),
        median_decile=float(np.median(arr)),
    )
