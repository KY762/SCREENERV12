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

The distortion is not always small. NBR did a 1-for-50 reverse split in 2020,
so its 2010 bars back-adjust from about $20 to about **$1,018** -- arithmetically
correct, and nothing a 2010 order could have paid. Any check with an absolute
price threshold in it (a minimum price filter, a "too few shares" rule) will
read a name like that wrongly, and should use raw prices via `adjusted=False`.

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


#: Sources whose stored volume is ALREADY split-adjusted to today's share
#: count, while their prices are raw. Measured 2026-09-28 across every stored
#: split: EODHD's share volume shows no step at a split (median log change
#: -0.03 over 999 forward splits, where raw volume would step +0.69), Tiingo's
#: steps as raw volume must (+0.54 forward, -1.22 reverse against +0.69 and
#: -1.61 expected). AAPL is the easy case to check by eye: ~335M shares a day
#: before the 2014 7-for-1 and ~300M after, at $645 and $94.
VENDOR_ADJUSTED_VOLUME = frozenset({"eodhd"})


def adjust_bars(
    bars: pd.DataFrame,
    splits: list[Split],
    *,
    all_splits: list[Split] | None = None,
    volume_already_adjusted: pd.Series | bool = False,
) -> pd.DataFrame:
    """Back-adjusted OHLCV. Prices divided by the factor, volume multiplied.

    Volume moves the opposite way because the same traded value is a different
    number of shares on each side of a split. Leaving volume raw would put a
    7x step into every liquidity measure on the ex-date.

    BUT only raw volume. `volume_already_adjusted` marks rows (a boolean Series
    on the bars' index, or one bool for all of them) whose vendor volume is
    already expressed in shares after EVERY split in `all_splits` -- EODHD's,
    see VENDOR_ADJUSTED_VOLUME. Those rows are first converted back to raw
    shares, then adjusted like any other. Multiplying them again, as this
    function did until 2026-09-28, overstated dollar volume by the product of
    every later split -- and since that product includes splits after the bar,
    whether a stock cleared a liquidity floor in 2012 depended on a split in
    2020. A reverse splitter, typically a distressed small cap, read as
    thinner than it was by the same factor.

    `all_splits` defaults to `splits`. Pass the full list when `splits` has been
    cut at a no-lookahead horizon: the vendor adjusted for every split it knew,
    not only the ones the run is allowed to see.

    The input frame is not modified.
    """
    everything = splits if all_splits is None else all_splits
    marked = volume_already_adjusted
    any_marked = bool(marked.any()) if isinstance(marked, pd.Series) else bool(marked)
    if bars.empty or (not splits and not (any_marked and everything)):
        return bars
    factor = cumulative_factor(splits, bars.index)
    out = bars.copy()
    for column in PRICE_COLUMNS:
        if column in out.columns:
            out[column] = out[column] / factor
    if "volume" in out.columns:
        volume = out["volume"]
        if any_marked and everything:
            vendor_factor = cumulative_factor(everything, bars.index)
            volume = volume.where(~marked, volume / vendor_factor) if isinstance(
                marked, pd.Series
            ) else volume / vendor_factor
        out["volume"] = volume * factor
    return out
