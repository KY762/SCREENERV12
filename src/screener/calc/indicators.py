"""Price and volume indicators.

All functions take a DataFrame with lowercase OHLCV columns and return a Series
aligned to the input index. Warmup periods are ``NaN``, never forward-filled or
back-filled -- a missing value means "not computable yet", and silently filling
it would fabricate history.

Smoothing convention
--------------------
``atr`` uses Wilder's smoothing (RMA), matching the default of TradingView's
``ta.atr`` and Wilder's original 1978 definition. Platforms that use a simple
mean of true range will produce different numbers; the difference is largest
immediately after the warmup period.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")


def _require(df: pd.DataFrame, cols: tuple[str, ...] = REQUIRED_COLUMNS) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"DataFrame missing required column(s): {missing}")


def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple moving average. NaN until ``window`` observations exist."""
    if window < 1:
        raise ValueError("window must be >= 1")
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    """Exponential moving average, alpha = 2/(window+1), seeded on the SMA.

    Seeding on the SMA (rather than the first observation) makes the result
    independent of how much history precedes the window, which matters when the
    same symbol is recomputed over different date ranges.
    """
    if window < 1:
        raise ValueError("window must be >= 1")
    return series.ewm(span=window, adjust=False, min_periods=window).mean()


def rma(series: pd.Series, window: int) -> pd.Series:
    """Wilder's smoothing: alpha = 1/window, seeded on the SMA of the first window."""
    if window < 1:
        raise ValueError("window must be >= 1")
    values = series.to_numpy(dtype="float64", copy=True)
    out = np.full(values.shape, np.nan)
    n = len(values)
    if n < window:
        return pd.Series(out, index=series.index, name=series.name)

    first = values[:window]
    if np.isnan(first).any():
        # Find the earliest window with no NaNs; before that nothing is computable.
        start = None
        for i in range(window, n + 1):
            if not np.isnan(values[i - window : i]).any():
                start = i
                break
        if start is None:
            return pd.Series(out, index=series.index, name=series.name)
    else:
        start = window

    acc = values[start - window : start].mean()
    out[start - 1] = acc
    for i in range(start, n):
        acc = (acc * (window - 1) + values[i]) / window
        out[i] = acc
    return pd.Series(out, index=series.index, name=series.name)


def true_range(df: pd.DataFrame) -> pd.Series:
    """True Range: max(H-L, |H-C_prev|, |L-C_prev|).

    The first bar has no previous close, so TR reduces to H-L there.
    """
    _require(df, ("high", "low", "close"))
    prev_close = df["close"].shift(1)
    hl = df["high"] - df["low"]
    hc = (df["high"] - prev_close).abs()
    lc = (df["low"] - prev_close).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    tr.iloc[0] = hl.iloc[0] if len(df) else np.nan
    return tr.rename("true_range")


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Average True Range using Wilder's smoothing. [CONVENTION: window=14]"""
    return rma(true_range(df), window).rename(f"atr_{window}")


def atr_pct(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """ATR as a fraction of close -- comparable across price levels."""
    return (atr(df, window) / df["close"]).rename(f"atr_pct_{window}")


def rvol(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Relative volume: today's volume over the trailing average.

    The denominator EXCLUDES the current bar. Including it would let a single
    huge volume day inflate its own baseline and mute the very signal being
    measured. [CONVENTION: window=20]
    """
    _require(df, ("volume",))
    baseline = df["volume"].shift(1).rolling(window=window, min_periods=window).mean()
    return (df["volume"] / baseline).rename(f"rvol_{window}")


def returns(series: pd.Series, periods: int) -> pd.Series:
    """Simple return over ``periods`` bars: (x[t] / x[t-periods]) - 1."""
    if periods < 1:
        raise ValueError("periods must be >= 1")
    return series.pct_change(periods=periods, fill_method=None).rename(f"ret_{periods}d")


def realized_vol(series: pd.Series, window: int) -> pd.Series:
    """Standard deviation of daily simple returns over ``window`` bars.

    Not annualized. Used as a denominator for volatility-adjusted momentum,
    where the annualization factor would cancel out anyway.
    """
    daily = series.pct_change(fill_method=None)
    return daily.rolling(window=window, min_periods=window).std(ddof=1).rename(f"vol_{window}")


def clv(df: pd.DataFrame) -> pd.Series:
    """Close Location Value: where the close sits within the bar's range.

    ``((C-L) - (H-C)) / (H-L)``, ranging from -1 (close at low) to +1 (close at
    high). Zero parameters. The cleanest single-bar proxy available from OHLCV
    for "who finished the session in control".

    A bar with H == L (no range) returns 0.0 rather than NaN -- there was no
    contest, so neither side won.
    """
    _require(df, ("high", "low", "close"))
    rng = df["high"] - df["low"]
    raw = ((df["close"] - df["low"]) - (df["high"] - df["close"]))
    out = raw.divide(rng).where(rng > 0, 0.0)
    return out.rename("clv")


def pct_from_high(df: pd.DataFrame, window: int = 252) -> pd.Series:
    """Distance below the rolling maximum high, as a negative fraction.

    ``0.0`` means the close is at the window high. ``-0.25`` means 25% below it.
    The window INCLUDES the current bar, so a new high reads exactly 0.0.
    [CONVENTION: window=252 trading days ~ one year]
    """
    _require(df, ("high", "close"))
    rolling_high = df["high"].rolling(window=window, min_periods=window).max()
    return ((df["close"] - rolling_high) / rolling_high).rename(f"pct_from_{window}d_high")


def dollar_volume(df: pd.DataFrame, window: int = 50) -> pd.Series:
    """Average daily dollar volume over ``window`` bars, using typical price."""
    _require(df, ("high", "low", "close", "volume"))
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    return (typical * df["volume"]).rolling(window=window, min_periods=window).mean().rename(
        f"dollar_vol_{window}"
    )


def slope_positive(series: pd.Series, lookback: int) -> pd.Series:
    """True where ``series[t] > series[t-lookback]``.

    Used for the SMA(200) rising filter. Returns a nullable boolean so warmup
    bars stay distinguishable from genuine False.
    """
    if lookback < 1:
        raise ValueError("lookback must be >= 1")
    prior = series.shift(lookback)
    out = series > prior
    return out.where(series.notna() & prior.notna()).astype("boolean").rename("slope_positive")
