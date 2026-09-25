"""Effective bid-ask spread, estimated from daily high and low prices.

The cost model in this project is a constant: 5 basis points a side, declared
in `CostModel` and never measured. On S&P 500 mega caps that is roughly right.
On the mid and small caps the universe is moving to it is not close, and the
difference decides results rather than decorating them:

    hold      turns/year    annual drag at 5bp    at 40bp
    20 days      ~12            0.6%               8.0%
    63 days       ~4            0.2%               2.6%

A strategy whose gross edge is a few percent a year is entirely determined by
which of those columns is true. So the cost has to become a measured input.

CORWIN & SCHULTZ (2012). The insight is that a daily high-low range contains
two things -- the security's true variance, which scales with time, and the
bid-ask spread, which does not. Comparing the range over two consecutive days
against the sum of the two single-day ranges separates them, because doubling
the period doubles the variance contribution but leaves the spread contribution
unchanged.

It needs only daily OHLC, which is what this database stores, and it is the
standard estimator for exactly this situation. Its own paper reports a
correlation above 0.9 with TAQ effective spreads on US equities.

WHAT IT IS NOT. It is an estimate of the QUOTED spread around the trade, not of
the total cost of a fill: it excludes commission, exchange fees, and the market
impact of the order itself. For a $300 position in a name trading $2M a day
impact is negligible, which is the one genuine advantage of a small account.
It also assumes the price follows a continuous diffusion, so an overnight gap
breaks it -- and the direction is the opposite of the intuitive one. A gap
inflates the TWO-DAY range while leaving the single-day ranges alone, which is
the signature the estimator reads as "no spread": alpha goes sharply negative
and the estimate floors at zero. So an uncorrected gapping session reports no
trading cost at all. That matters here specifically, because a momentum rule
buys names that have just gapped on news, and their costs would be the ones
silently set to zero. `adjust_for_gaps` applies the paper's correction.

Negative estimates are set to zero rather than dropped. The estimator is noisy
day to day and negatives are expected; discarding them keeps only the upward
errors and biases the average high, which is exactly the wrong direction for a
number used to judge whether an edge survives costs.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

#: 3 - 2*sqrt(2), the constant that falls out of the two-day variance algebra.
K = 3.0 - 2.0 * np.sqrt(2.0)


def corwin_schultz(
    bars: pd.DataFrame, *, adjust_for_gaps: bool = True
) -> pd.Series:
    """Estimated proportional effective spread, one value per day.

    Returns a fraction: 0.004 means 40 basis points round trip, so a half-turn
    costs about 20bp. Indexed like `bars`, with the first row NaN because the
    estimator needs two consecutive sessions.

    `adjust_for_gaps` applies the paper's overnight correction. Without it an
    earnings gap inflates the two-day range, drives the estimate negative and
    floors it to zero -- so the gapping session reports NO cost, understating
    exactly the names a momentum rule buys.
    """
    if len(bars) < 2 or not {"high", "low"} <= set(bars.columns):
        return pd.Series(np.nan, index=bars.index, dtype="float64")

    high = bars["high"].to_numpy(dtype="float64").copy()
    low = bars["low"].to_numpy(dtype="float64").copy()

    if adjust_for_gaps and "close" in bars.columns:
        close = bars["close"].to_numpy(dtype="float64")
        # Where today's whole range sits above yesterday's close, the gap is
        # price movement rather than spread; shift the range down by it. The
        # mirror case shifts up. Corwin & Schultz (2012) section 1.3.
        prev_close = np.concatenate(([np.nan], close[:-1]))
        gap_up = np.where(low > prev_close, low - prev_close, 0.0)
        gap_dn = np.where(high < prev_close, high - prev_close, 0.0)
        gap = np.nan_to_num(gap_up + gap_dn)
        high = high - gap
        low = low - gap

    with np.errstate(divide="ignore", invalid="ignore"):
        # One-day log ranges, today and yesterday.
        single = np.log(high / low) ** 2
        beta = single[1:] + single[:-1]

        # The two-day range: highest high and lowest low across the pair.
        two_day_high = np.maximum(high[1:], high[:-1])
        two_day_low = np.minimum(low[1:], low[:-1])
        gamma = np.log(two_day_high / two_day_low) ** 2

        alpha = (np.sqrt(2.0 * beta) - np.sqrt(beta)) / K - np.sqrt(gamma / K)
        spread = 2.0 * (np.exp(alpha) - 1.0) / (1.0 + np.exp(alpha))

    # A negative estimate means the noise ran the other way this pair. Floor at
    # zero rather than dropping: dropping keeps only upward errors and biases
    # the mean high, which would make costs look worse than they are.
    spread = np.where(np.isfinite(spread), np.maximum(spread, 0.0), np.nan)
    return pd.Series(
        np.concatenate(([np.nan], spread)), index=bars.index, dtype="float64"
    )


def typical_spread(bars: pd.DataFrame, *, window: int = 21) -> pd.Series:
    """Rolling median of the daily estimate.

    The median rather than the mean: the daily series is noisy and right-
    skewed, and one halted or gapping session should not set the cost assumed
    for a month of trading.
    """
    daily = corwin_schultz(bars)
    return daily.rolling(window, min_periods=max(2, window // 2)).median()


def round_trip_cost(spread: float, slippage_bps: float = 0.0) -> float:
    """What one complete trade costs, as a fraction of notional.

    Crossing the spread on the way in and again on the way out is one full
    spread, not two: the quoted spread already spans both sides, so a buy at
    the ask and a sell at the bid gives up `spread` in total. Charging two
    would double-count, which is the most common way this arithmetic goes
    wrong.
    """
    return float(spread) + 2.0 * (slippage_bps / 10_000.0)


def annual_drag(spread: float, hold_days: int, slippage_bps: float = 0.0) -> float:
    """Cost as a fraction of capital per year, at a given holding period.

    Roughly 252 trading days a year divided by the hold gives the number of
    round trips a fully invested position makes. This is what decides whether
    a small edge survives: the same spread costs four times as much at a
    20-day hold as at 80 days.
    """
    if hold_days <= 0:
        return float("nan")
    turns = 252.0 / hold_days
    return round_trip_cost(spread, slippage_bps) * turns


def spread_table(
    bars_by_symbol: Mapping[str, pd.DataFrame], *, window: int = 21
) -> dict[str, pd.Series]:
    """Trailing per-symbol spread estimates, one series per ticker.

    SHIFTED ONE SESSION, and that shift is the whole safety argument. A rolling
    window ending on day D includes D's own high and low, which are not known
    until D closes. The engine fills at D's OPEN. Charging a cost derived from
    the range of the day being traded is lookahead -- small, plausible-looking,
    and exactly the shape of the four defects already found in this project.
    So the value stamped on day D is the median through D-1.

    Symbols with too little history are absent from the table rather than
    present with a guess; `CostModel` falls back to its flat rate for those,
    which is the conservative direction only when the flat rate is the higher
    of the two, so the fallback is deliberately set high.
    """
    table: dict[str, pd.Series] = {}
    for ticker, frame in bars_by_symbol.items():
        if len(frame) < window or not {"high", "low"} <= set(frame.columns):
            continue
        series = typical_spread(frame, window=window).shift(1)
        series = series.dropna()
        if series.empty:
            continue
        table[ticker] = series
    return table
