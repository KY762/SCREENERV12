"""Range compression and expansion.

The Round 2 candidate carried forward from docs/04 section 5.6, and the one
concept in the operator's framework with a mechanism behind it rather than a
folk pattern: volatility clusters. Quiet periods are followed by quiet periods
until they are not, and the transition is the event.

That is Auction Market Theory's balance-to-imbalance transition expressed on
daily bars -- the same idea the journal already works in, computable without
intraday data.

Nothing here claims the expansion resolves upward. Direction is what the trend
filter and the entry rule are for; this module only identifies the state.
"""

from __future__ import annotations

import pandas as pd

from .indicators import atr, sma


def atr_ratio(df: pd.DataFrame, fast: int = 14, slow: int = 50) -> pd.Series:
    """ATR(fast) / ATR(slow). Below 1 means recent range is unusually quiet.

    A ratio rather than a level, so it is comparable across instruments and
    across price levels without a second parameter.
    """
    quick = atr(df, fast)
    slow_atr = atr(df, slow)
    return (quick / slow_atr.where(slow_atr > 0)).rename(f"atr_ratio_{fast}_{slow}")


def range_percentile(df: pd.DataFrame, window: int = 126, atr_window: int = 14) -> pd.Series:
    """Where today's ATR sits in its own trailing distribution, 0.0 to 1.0.

    Percentile rather than a threshold on the raw value: what counts as quiet
    for a utility is not what counts as quiet for a semiconductor, and a
    cross-sectional threshold would silently select by sector.
    """
    series = atr(df, atr_window)
    return (
        series.rolling(window, min_periods=window)
        .rank(pct=True)
        .rename(f"range_pct_{window}")
    )


def is_compressed(
    df: pd.DataFrame, percentile: float = 0.20, window: int = 126, atr_window: int = 14
) -> pd.Series:
    """True where ATR sits in the lowest ``percentile`` of its own history."""
    return (range_percentile(df, window, atr_window) <= percentile).rename("compressed")


def expansion_events(
    df: pd.DataFrame,
    *,
    percentile: float = 0.20,
    window: int = 126,
    atr_window: int = 14,
    breakout_window: int = 20,
    min_compressed_bars: int = 5,
    stop_buffer_atr: float = 0.10,
    trend_mask: pd.Series | None = None,
) -> list:
    """Compression, then an upward break of the compressed range.

    The trigger is a close above the highest high of the preceding
    ``breakout_window`` bars while the compression condition held. The stop
    goes below the compressed range's low, because that is the level whose
    violation says the compression resolved the other way.
    """
    from .patterns import SignalEvent

    compressed = is_compressed(df, percentile, window, atr_window)
    atr_series = atr(df, atr_window)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # Highest high strictly BEFORE the current bar -- including today's own high
    # would make the breakout condition trivially true.
    prior_high = high.rolling(breakout_window, min_periods=breakout_window).max().shift(1)
    prior_low = low.rolling(breakout_window, min_periods=breakout_window).min().shift(1)
    run = compressed.rolling(min_compressed_bars, min_periods=min_compressed_bars).sum()

    trend = (
        trend_mask.fillna(False)
        if trend_mask is not None
        else pd.Series(True, index=df.index)
    )

    events = []
    n = len(df)
    armed = False
    for i in range(n):
        if i + 1 >= n:
            break
        was_quiet = bool(run.iloc[i] == min_compressed_bars) if not pd.isna(run.iloc[i]) else False
        if was_quiet:
            armed = True
        if not armed:
            continue

        threshold = prior_high.iloc[i]
        atr_value = atr_series.iloc[i]
        if pd.isna(threshold) or pd.isna(atr_value) or atr_value <= 0:
            continue
        if not bool(trend.iloc[i]):
            continue

        if close.iloc[i] > threshold:
            floor = prior_low.iloc[i]
            if pd.isna(floor):
                continue
            events.append(
                SignalEvent(
                    setup="range_expansion",
                    formation_idx=i,
                    trigger_idx=i,
                    entry_idx=i + 1,
                    stop_level=float(floor) - stop_buffer_atr * float(atr_value),
                    zone_bottom=float(floor),
                    zone_top=float(threshold),
                )
            )
            armed = False        # one entry per compression episode
    return events


def effort_vs_result(
    df: pd.DataFrame, atr_window: int = 14, volume_window: int = 20
) -> pd.Series:
    """(range / ATR) / (volume / average volume) -- docs/05 section 2.2.3.

    Low means heavy volume moved price very little: absorption, someone filling
    size against the move. High means price travelled on light volume: a thin
    market with little opposition.

    The closest end-of-day expression of what a footprint chart measures. Not
    equivalent -- it asks the same question with the data actually available.
    """
    span = (df["high"] - df["low"])
    normalised_range = span / atr(df, atr_window).where(lambda s: s > 0)
    relative_volume = df["volume"] / sma(df["volume"], volume_window).where(lambda s: s > 0)
    return (normalised_range / relative_volume.where(relative_volume > 0)).rename(
        "effort_vs_result"
    )
