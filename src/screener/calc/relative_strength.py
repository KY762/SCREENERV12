"""Relative strength and cross-sectional ranking.

The volatility adjustment here is not cosmetic. Raw momentum ranking
systematically favours high-volatility names -- they simply move more, in both
directions -- so a "strength" decile built on raw returns is partly a volatility
portfolio. That is exactly the confound the random-selection benchmark exists to
detect, and dividing by realized volatility removes it at zero parameter cost.
"""

from __future__ import annotations

import pandas as pd

from .indicators import realized_vol, returns


def relative_strength(
    symbol_close: pd.Series, benchmark_close: pd.Series, lookback: int
) -> pd.Series:
    """Excess return over the benchmark across ``lookback`` bars.

    Both series are aligned on their index first; bars where either is missing
    yield NaN rather than a silently mismatched comparison.
    """
    aligned_symbol, aligned_benchmark = symbol_close.align(benchmark_close, join="inner")
    excess = returns(aligned_symbol, lookback) - returns(aligned_benchmark, lookback)
    return excess.rename(f"rs_{lookback}d")


def relative_strength_adjusted(
    symbol_close: pd.Series, benchmark_close: pd.Series, lookback: int
) -> pd.Series:
    """Volatility-adjusted relative strength: excess return per unit of risk.

    The approved H1 ranking input (docs/04 section 5.1).
    """
    aligned_symbol, aligned_benchmark = symbol_close.align(benchmark_close, join="inner")
    excess = returns(aligned_symbol, lookback) - returns(aligned_benchmark, lookback)
    vol = realized_vol(aligned_symbol, lookback)
    out = excess / vol.where(vol > 0)
    return out.rename(f"rs_adj_{lookback}d")


def cross_sectional_rank(values: pd.Series, ascending: bool = False) -> pd.Series:
    """Percentile rank within a cross-section, 0.0 to 1.0.

    ``ascending=False`` means the largest value ranks 1.0. NaNs stay NaN -- a
    symbol without a computable metric is excluded, not ranked last.
    """
    return values.rank(pct=True, ascending=ascending, na_option="keep")


def composite_rank(frame: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.Series:
    """Equal- or custom-weighted mean of per-column percentile ranks.

    Ranking before combining makes the inputs commensurable -- averaging a
    return with a volume ratio directly would let whichever has the wider
    numeric spread dominate the result.
    """
    ranks = pd.DataFrame(
        {col: cross_sectional_rank(frame[col]) for col in frame.columns},
        index=frame.index,
    )
    if weights is None:
        return ranks.mean(axis=1, skipna=False).rename("composite_rank")
    missing = set(weights) - set(frame.columns)
    if missing:
        raise ValueError(f"weights reference unknown column(s): {sorted(missing)}")
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("weights must sum to a positive value")
    weighted = sum(ranks[col] * w for col, w in weights.items()) / total
    return weighted.rename("composite_rank")
