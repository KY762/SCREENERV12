"""Price-structure geometry: Fair Value Gaps, Inverse FVGs, swings, liquidity sweeps.

These are the mechanized forms of the operator's ICT/Smart Money concepts. Each
has an exact geometric definition -- which is precisely why they survived the
mechanization screen in the trader profile while Fibonacci retracements did not.

Normalization convention
------------------------
Where a bar's size is compared to volatility, the ATR baseline is taken from the
bar BEFORE it. A large bar would otherwise inflate the average it is measured
against, muting the signal being detected. Same reasoning as ``indicators.rvol``.

Lookahead
---------
Gap formation, gap entry, and sweep detection are all knowable at the bar they
are reported on. Swing pivots are NOT: a pivot at index ``i`` needs ``right``
subsequent bars to confirm. Use ``confirmed_swing_low_price`` for anything that
feeds a trading decision -- it reports only pivots already confirmed as of each
bar. ``swing_low_pivots`` marks the pivot bar itself and is for analysis only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .indicators import atr


# --------------------------------------------------------------------------
# Fair Value Gaps
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Gap:
    """A Fair Value Gap. Indices are positional (iloc), not labels."""

    formation_idx: int
    direction: str  # "bullish" | "bearish"
    bottom: float
    top: float

    @property
    def size(self) -> float:
        return self.top - self.bottom


def find_gaps(df: pd.DataFrame, direction: str = "bullish") -> list[Gap]:
    """Locate Fair Value Gaps.

    Bullish (a gap left by an up-move)::

        high[t-2] < low[t]        zone = [high[t-2], low[t]]

    Bearish (a gap left by a down-move)::

        low[t-2] > high[t]        zone = [high[t], low[t-2]]

    Both are fully determined at bar ``t``.
    """
    if direction not in ("bullish", "bearish"):
        raise ValueError("direction must be 'bullish' or 'bearish'")

    high = df["high"].to_numpy(dtype="float64")
    low = df["low"].to_numpy(dtype="float64")
    gaps: list[Gap] = []

    for t in range(2, len(df)):
        if direction == "bullish":
            if high[t - 2] < low[t]:
                gaps.append(Gap(t, "bullish", float(high[t - 2]), float(low[t])))
        else:
            if low[t - 2] > high[t]:
                gaps.append(Gap(t, "bearish", float(high[t]), float(low[t - 2])))
    return gaps


def displacement_ratio(
    df: pd.DataFrame, measure: str = "body", atr_window: int = 14
) -> pd.Series:
    """Bar size relative to prior ATR, for the displacement filter.

    ``measure``:
      - ``"body"``  -- ``|close - open| / ATR_prev``. Most faithful to the concept:
        displacement denotes directional commitment, and a long-wicked doji has
        large range but zero displacement.
      - ``"range"`` -- ``(high - low) / ATR_prev``. Conflates directional force
        with two-sided rejection.

    ``"gap"`` is not offered here -- gap size is a property of the Gap object,
    and is likely partly redundant with body (see docs/05 section 1).
    """
    if measure not in ("body", "range"):
        raise ValueError("measure must be 'body' or 'range'")
    baseline = atr(df, atr_window).shift(1)
    if measure == "body":
        magnitude = (df["close"] - df["open"]).abs()
    else:
        magnitude = df["high"] - df["low"]
    return (magnitude / baseline).rename(f"displacement_{measure}")


# --------------------------------------------------------------------------
# Swing pivots
# --------------------------------------------------------------------------

def swing_low_pivots(df: pd.DataFrame, left: int = 2, right: int = 2) -> pd.Series:
    """Boolean Series marking swing-low pivot bars.

    A pivot at ``i`` has ``low[i]`` strictly below the ``left`` bars before it and
    at or below the ``right`` bars after it.

    LOOKAHEAD WARNING: the mark sits on bar ``i`` but is not knowable until bar
    ``i + right``. Do not feed this to a trading rule; use
    ``confirmed_swing_low_price`` instead.
    """
    low = df["low"].to_numpy(dtype="float64")
    n = len(low)
    out = np.zeros(n, dtype=bool)
    for i in range(left, n - right):
        window_left = low[i - left : i]
        window_right = low[i + 1 : i + right + 1]
        if (low[i] < window_left).all() and (low[i] <= window_right).all():
            out[i] = True
    return pd.Series(out, index=df.index, name="swing_low_pivot")


def confirmed_swing_low_price(
    df: pd.DataFrame, left: int = 2, right: int = 2
) -> pd.Series:
    """Price of the most recent swing low CONFIRMED as of each bar.

    Lookahead-safe: a pivot at ``i`` first appears in the output at ``i + right``.
    NaN until the first confirmation.
    """
    pivots = swing_low_pivots(df, left, right).to_numpy()
    low = df["low"].to_numpy(dtype="float64")
    n = len(low)
    out = np.full(n, np.nan)
    latest = np.nan
    for t in range(n):
        pivot_idx = t - right
        if pivot_idx >= 0 and pivots[pivot_idx]:
            latest = low[pivot_idx]
        out[t] = latest
    return pd.Series(out, index=df.index, name="confirmed_swing_low")


# --------------------------------------------------------------------------
# Liquidity references
# --------------------------------------------------------------------------

def liquidity_reference(
    df: pd.DataFrame, kind: str = "n_bar", n: int = 10, left: int = 2, right: int = 2
) -> pd.Series:
    """The low level a sweep would target, as of each bar.

    All variants EXCLUDE the current bar -- the reference must pre-exist the
    sweep, or the test is circular.

    ``kind``:
      - ``"prior_day"``  -- ``low[t-1]``
      - ``"prior_week"`` -- min low of the prior 5 sessions
      - ``"n_bar"``      -- min low of the prior ``n`` sessions
      - ``"swing"``      -- most recent confirmed swing low
    """
    if kind == "prior_day":
        return df["low"].shift(1).rename("liq_ref_prior_day")
    if kind == "prior_week":
        return (
            df["low"].shift(1).rolling(window=5, min_periods=5).min().rename("liq_ref_prior_week")
        )
    if kind == "n_bar":
        return (
            df["low"].shift(1).rolling(window=n, min_periods=n).min().rename(f"liq_ref_{n}bar")
        )
    if kind == "swing":
        return confirmed_swing_low_price(df, left, right).shift(1).rename("liq_ref_swing")
    raise ValueError(f"unknown liquidity reference kind: {kind!r}")


def sweep_reclaim(df: pd.DataFrame, reference: pd.Series) -> pd.Series:
    """Boolean: bar swept below ``reference`` and closed back above it.

    ``low[t] < reference[t]`` AND ``close[t] > reference[t]``.

    The same-session reclaim is what distinguishes this from catching a falling
    knife -- the level was taken and immediately rejected.
    """
    swept = df["low"] < reference
    reclaimed = df["close"] > reference
    valid = reference.notna()
    return (swept & reclaimed & valid).rename("sweep_reclaim")


# --------------------------------------------------------------------------
# Signal events
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class SignalEvent:
    """A detected setup. ``entry_idx`` is the bar the trigger completed on;
    execution is assumed at the NEXT bar's open."""

    setup: str
    formation_idx: int
    trigger_idx: int
    entry_idx: int
    stop_level: float
    zone_bottom: float
    zone_top: float


def fvg_entry_events(
    df: pd.DataFrame,
    *,
    retrace_window: int = 10,
    stop_buffer_atr: float = 0.10,
    atr_window: int = 14,
    min_gap_atr: float = 0.0,
    displacement_min: float | None = None,
    displacement_measure: str = "body",
    trend_mask: pd.Series | None = None,
) -> list[SignalEvent]:
    """H2 -- bullish FVG forms, price retraces into it and holds.

    Entry when ``low[k] <= gap_top`` and ``close[k] > gap_bottom`` within
    ``retrace_window`` bars. The gap is INVALIDATED and discarded if any close
    falls below ``gap_bottom`` first.

    ``displacement_min=None`` disables the displacement filter entirely -- the
    null that displacement contributes nothing is a live hypothesis.
    """
    atr_series = atr(df, atr_window).to_numpy(dtype="float64")
    close = df["close"].to_numpy(dtype="float64")
    low = df["low"].to_numpy(dtype="float64")
    n = len(df)

    disp = (
        displacement_ratio(df, displacement_measure, atr_window).to_numpy(dtype="float64")
        if displacement_min is not None
        else None
    )
    trend = (
        trend_mask.fillna(False).to_numpy(dtype=bool)
        if trend_mask is not None
        else np.ones(n, dtype=bool)
    )

    events: list[SignalEvent] = []
    for gap in find_gaps(df, "bullish"):
        f = gap.formation_idx
        a = atr_series[f]
        if np.isnan(a) or a <= 0:
            continue
        if min_gap_atr > 0 and gap.size < min_gap_atr * a:
            continue
        if disp is not None:
            d = disp[f - 1]
            if np.isnan(d) or d < displacement_min:
                continue
        if not trend[f]:
            continue

        for k in range(f + 1, min(f + 1 + retrace_window, n)):
            if close[k] < gap.bottom:
                break  # invalidated
            if low[k] <= gap.top and close[k] > gap.bottom:
                if k + 1 >= n:
                    break
                events.append(
                    SignalEvent(
                        setup="fvg_continuation",
                        formation_idx=f,
                        trigger_idx=k,
                        entry_idx=k + 1,
                        stop_level=gap.bottom - stop_buffer_atr * a,
                        zone_bottom=gap.bottom,
                        zone_top=gap.top,
                    )
                )
                break
    return events


def ifvg_entry_events(
    df: pd.DataFrame,
    *,
    inversion_window: int = 10,
    retrace_window: int = 10,
    stop_buffer_atr: float = 0.10,
    atr_window: int = 14,
    min_gap_atr: float = 0.0,
    trend_mask: pd.Series | None = None,
) -> list[SignalEvent]:
    """H4 -- bullish Inverse FVG.

    A BEARISH gap forms, price later closes above it (the inversion), and then
    retests the inverted zone as support.

    Three sequential conditions, so sample shrinks multiplicatively -- the
    confluence-stacking effect documented in docs/05 section 1.4.
    """
    atr_series = atr(df, atr_window).to_numpy(dtype="float64")
    close = df["close"].to_numpy(dtype="float64")
    low = df["low"].to_numpy(dtype="float64")
    n = len(df)
    trend = (
        trend_mask.fillna(False).to_numpy(dtype=bool)
        if trend_mask is not None
        else np.ones(n, dtype=bool)
    )

    events: list[SignalEvent] = []
    for gap in find_gaps(df, "bearish"):
        f = gap.formation_idx
        a = atr_series[f]
        if np.isnan(a) or a <= 0:
            continue
        if min_gap_atr > 0 and gap.size < min_gap_atr * a:
            continue

        inversion_idx = None
        for j in range(f + 1, min(f + 1 + inversion_window, n)):
            if close[j] > gap.top:
                inversion_idx = j
                break
        if inversion_idx is None:
            continue

        for k in range(inversion_idx + 1, min(inversion_idx + 1 + retrace_window, n)):
            if close[k] < gap.bottom:
                break  # inversion failed
            if low[k] <= gap.top and close[k] > gap.bottom:
                if k + 1 >= n or not trend[k]:
                    break
                events.append(
                    SignalEvent(
                        setup="ifvg_reversal",
                        formation_idx=f,
                        trigger_idx=k,
                        entry_idx=k + 1,
                        stop_level=gap.bottom - stop_buffer_atr * a,
                        zone_bottom=gap.bottom,
                        zone_top=gap.top,
                    )
                )
                break
    return events


def sweep_entry_events(
    df: pd.DataFrame,
    *,
    reference_kind: str = "n_bar",
    n_bar: int = 10,
    stop_buffer_atr: float = 0.10,
    atr_window: int = 14,
    require_upper_half_close: bool = False,
    trend_mask: pd.Series | None = None,
) -> list[SignalEvent]:
    """H3 -- liquidity sweep and same-session reclaim."""
    reference = liquidity_reference(df, reference_kind, n_bar)
    triggered = sweep_reclaim(df, reference)

    if require_upper_half_close:
        midpoint = (df["high"] + df["low"]) / 2.0
        triggered = triggered & (df["close"] > midpoint)
    if trend_mask is not None:
        triggered = triggered & trend_mask.fillna(False)

    atr_series = atr(df, atr_window)
    n = len(df)
    events: list[SignalEvent] = []
    positions = np.flatnonzero(triggered.to_numpy(dtype=bool))

    for t in positions:
        if t + 1 >= n:
            continue
        a = atr_series.iloc[t]
        if pd.isna(a) or a <= 0:
            continue
        bar_low = float(df["low"].iloc[t])
        events.append(
            SignalEvent(
                setup=f"sweep_{reference_kind}",
                formation_idx=int(t),
                trigger_idx=int(t),
                entry_idx=int(t) + 1,
                stop_level=bar_low - stop_buffer_atr * float(a),
                zone_bottom=bar_low,
                zone_top=float(reference.iloc[t]),
            )
        )
    return events
