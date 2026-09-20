"""Split adjustment, derived on demand from stored corporate actions.

`price_daily` holds RAW prices (non-negotiable 2) because storing adjusted ones
makes history mutate at every future split. The cost of that choice is that a
split is a real discontinuity in the stored series, and something has to remove
it before any return is computed. Until 2026-09-19 nothing did, and the
`corporate_actions` table was empty, so every split was a fake return:

    AAPL  7-for-1, 2014-06-09    read as a -81.7% 63-day return, RS -8.21
    C     1-for-10 reverse, 2011-05-09   read as a +765.6% return, RS +6.92
    ETFC  1-for-10 reverse, 2010-06-02   read as a +662.9% return, RS +5.58

That is not a rounding error in a momentum rule, it is the rule inverted:
Apple after a forward split ranks last and is never bought, while a distressed
bank doing a reverse split to keep its listing ranks first and is. 81 index
members and 130 such events sit inside the 2010-2015 development window alone.

BACK-ADJUSTED, not forward-adjusted. Prices before a split are divided by the
splits that came after them, so the most recent bar is the price actually
traded and history is scaled to match it. Returns are then correct everywhere,
and a position held through a split needs no special case: the share count and
the price move together by construction.

What this costs, recorded rather than hidden: historical prices are no longer
what an order would have paid. A 2012 AAPL bar reads about $90 rather than
$630. Dollar exposure and returns are unaffected -- seven times the shares at a
seventh of the price is the same position -- but anything reasoning about the
SHARE count at a past date is now reasoning about a notional one. That matters
for `calc/tradeability.py`, whose whole question is how many whole shares
$10,000 buys, and its answers for pre-split dates should be read as notional.

Dividends are deliberately excluded. They are not a discontinuity in the price
a backtest fills at, and adjusting a fill price for them would misstate the
fill. This module fixes the break in the series, not total return.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

PRICE_COLUMNS = ("open", "high", "low", "close")


@dataclass(frozen=True)
class Split:
    """One split. `ratio` is shares after over shares before.

    A 7-for-1 forward split is 7.0 and a 1-for-10 reverse split is 0.1. The
    price rule is the same for both: price_after = price_before / ratio.
    """

    ex_date: date
    ratio: float


def cumulative_factor(splits: list[Split], index: pd.DatetimeIndex) -> pd.Series:
    """For each date, the product of every split that comes strictly after it.

    `ex_date` is the first day quoted at the new price, so a bar ON the ex-date
    is already adjusted and only bars BEFORE it need scaling. Verified against
    stored data: AAPL closed 645.57 on 2014-06-06 and 93.70 on 2014-06-09, and
    645.57 / 7 = 92.2.

    Returns all-ones when there are no splits, so a caller need not special-case
    the common path.
    """
    factor = pd.Series(1.0, index=index)
    if not splits:
        return factor
    for split in splits:
        if split.ratio <= 0:
            continue
        before = index < pd.Timestamp(split.ex_date)
        factor.loc[before] = factor.loc[before] * split.ratio
    return factor


def adjust_bars(bars: pd.DataFrame, splits: list[Split]) -> pd.DataFrame:
    """Back-adjusted OHLCV. Prices divided by the factor, volume multiplied.

    Volume moves the opposite way because the same traded value is a different
    number of shares on each side of a split. Leaving volume raw would put a
    7x step into every liquidity measure on the ex-date.

    The input frame is not modified.
    """
    if bars.empty or not splits:
        return bars
    factor = cumulative_factor(splits, bars.index)
    out = bars.copy()
    for column in PRICE_COLUMNS:
        if column in out.columns:
            out[column] = out[column] / factor
    if "volume" in out.columns:
        out["volume"] = out["volume"] * factor
    return out
