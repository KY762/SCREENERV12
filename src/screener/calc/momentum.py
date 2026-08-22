"""Momentum measures with an explicit skip period.

The canonical equity momentum anomaly is 12-month-minus-1-month: rank on the
return from t-252 to t-21, deliberately EXCLUDING the most recent month. The
skip is not a detail. Short-horizon returns exhibit reversal, so including the
last month mixes a reversal signal into a continuation signal and blunts both.

That is the version with decades of replication behind it (Jegadeesh & Titman
1993; Fama & French 2012 for the international evidence). Round 1's H1 tested a
63-day lookback with no skip and a stop attached -- a short-horizon cousin the
literature does not support, which is worth stating plainly now that it failed.
"""

from __future__ import annotations

import pandas as pd

from .indicators import realized_vol


def momentum_skip(close: pd.Series, lookback: int = 252, skip: int = 21) -> pd.Series:
    """Return from ``t-lookback`` to ``t-skip``, as a fraction.

    ``skip=0`` gives an ordinary trailing return. ``lookback=252, skip=21`` is
    the canonical 12-1 formation.
    """
    if lookback <= skip:
        raise ValueError("lookback must exceed skip")
    past = close.shift(lookback)
    recent = close.shift(skip)
    out = (recent - past) / past.where(past > 0)
    return out.rename(f"mom_{lookback}_{skip}")


def relative_momentum_skip(
    symbol_close: pd.Series,
    benchmark_close: pd.Series,
    lookback: int = 252,
    skip: int = 21,
) -> pd.Series:
    """12-1 momentum in excess of a benchmark, both measured over the same
    window so the comparison is like for like."""
    a, b = symbol_close.align(benchmark_close, join="inner")
    out = momentum_skip(a, lookback, skip) - momentum_skip(b, lookback, skip)
    return out.rename(f"rel_mom_{lookback}_{skip}")


def volatility_scaled_momentum(
    close: pd.Series, lookback: int = 252, skip: int = 21, vol_window: int = 63
) -> pd.Series:
    """Momentum per unit of realized volatility.

    Same argument as ``relative_strength_adjusted``: an unscaled ranking is
    partly a volatility ranking, because high-volatility names simply move more
    in both directions.
    """
    raw = momentum_skip(close, lookback, skip)
    vol = realized_vol(close, vol_window)
    out = raw / vol.where(vol > 0)
    return out.rename(f"mom_adj_{lookback}_{skip}")


def month_end_mask(index: pd.DatetimeIndex) -> pd.Series:
    """True on the last available trading day of each month.

    Monthly rebalancing is part of the canonical specification, not a
    convenience: the anomaly is documented at monthly frequency, and rebalancing
    daily both changes the effect being measured and multiplies costs.
    """
    frame = pd.Series(index, index=index)
    periods = frame.dt.to_period("M")
    last = periods != periods.shift(-1)
    return pd.Series(last.to_numpy(), index=index, name="month_end")
