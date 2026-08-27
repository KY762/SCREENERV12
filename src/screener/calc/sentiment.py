"""A fear and greed composite, built only from series this project ingests.

The construction follows CNN's published one closely enough to be recognisable
-- breadth, price strength, momentum, volatility, safe-haven demand, junk-bond
demand, participation -- because a familiar scale is easier to sanity-check
than a bespoke one. Every component is computed from daily bars and the
`metrics_daily` columns already stored, plus the bond and commodity ETFs in
the candidate pool. Nothing here needs options data or a VIX feed.

WHAT THIS IS NOT. It is an observable, not a signal. No hypothesis in this
project has established that regime state predicts anything, and the H5
development run is a live warning about reading regime splits as evidence:
its expectancy was +0.029R in one bull window and -0.176R in one chop window,
on 43 and 44 trades. That is three buckets of noise, not a validated filter.
Until a pre-registered test says otherwise, this gauge describes where the
market has been, not what to do about it.

Each raw component is converted to 0-100 by its percentile rank inside a
TRAILING window, never the full sample. A full-sample rank would let a
reading at 2013 know about 2015, which is the lookahead rule in
non-negotiable 1. The trailing window is why early dates return NaN rather
than a fabricated midpoint.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# Two years of sessions. Long enough that a rank means something, short enough
# that a decade-old regime does not anchor today's reading.
RANK_WINDOW = 504

# Below this many observations a percentile is arithmetic, not information.
MIN_RANK_OBSERVATIONS = 126

COMPONENTS = (
    "breadth",
    "price_strength",
    "momentum",
    "volatility",
    "safe_haven",
    "junk_demand",
    "participation",
)

# Where each component sits on the scale. 0 is maximum fear, 100 maximum greed.
BANDS = (
    (0, 25, "extreme fear"),
    (25, 45, "fear"),
    (45, 55, "neutral"),
    (55, 75, "greed"),
    (75, 101, "extreme greed"),
)


def label_for(score: float) -> str:
    """The band a 0-100 score falls in."""
    for low, high, name in BANDS:
        if low <= score < high:
            return name
    return "unknown"


def trailing_percentile(
    series: pd.Series,
    window: int = RANK_WINDOW,
    min_periods: int = MIN_RANK_OBSERVATIONS,
) -> pd.Series:
    """Percentile rank of each value within the preceding `window` values.

    Point-in-time by construction: the rank at date t is computed from the
    window ending at t, so it never consults a future observation. Values
    before `min_periods` are NaN -- an honest gap, not a filled midpoint.
    """
    if series.empty:
        return pd.Series(dtype="float64")

    def rank_of_last(values: pd.Series) -> float:
        last = values.iloc[-1]
        if pd.isna(last):
            return float("nan")
        valid = values.dropna()
        if len(valid) < 2:
            return float("nan")
        return float((valid <= last).sum() - 1) / float(len(valid) - 1) * 100.0

    return series.rolling(window, min_periods=min_periods).apply(
        rank_of_last, raw=False
    )


def breadth_above_200(metrics: pd.DataFrame) -> pd.Series:
    """Share of the universe trading above its own 200-day average, per date.

    `metrics` is long-form: a date index with one row per symbol per date and
    an `above_sma_200` boolean column.
    """
    if metrics.empty or "above_sma_200" not in metrics.columns:
        return pd.Series(dtype="float64")
    return metrics.groupby(level=0)["above_sma_200"].mean() * 100.0


def price_strength(metrics: pd.DataFrame, within_pct: float = 0.05) -> pd.Series:
    """Share of the universe within `within_pct` of its 252-day high.

    `pct_from_252d_high` is stored as a negative fraction below the high, so
    -0.05 is five percent off. Near-highs is the greed end of this component.
    """
    if metrics.empty or "pct_from_252d_high" not in metrics.columns:
        return pd.Series(dtype="float64")
    near = metrics["pct_from_252d_high"] >= -abs(within_pct)
    return near.groupby(level=0).mean() * 100.0


def participation(metrics: pd.DataFrame) -> pd.Series:
    """Median relative volume across the universe.

    Rising participation accompanies both panics and melt-ups, so this is the
    weakest of the seven on its own. It earns its place by moving when the
    price-based components have not yet.
    """
    if metrics.empty or "rvol_20" not in metrics.columns:
        return pd.Series(dtype="float64")
    return metrics.groupby(level=0)["rvol_20"].median()


def momentum_vs_average(closes: pd.Series, window: int = 125) -> pd.Series:
    """Index level relative to its own `window`-day average, as a fraction."""
    if closes.empty:
        return pd.Series(dtype="float64")
    average = closes.rolling(window, min_periods=window).mean()
    return (closes / average) - 1.0


def realized_volatility(closes: pd.Series, window: int = 21) -> pd.Series:
    """Annualised realised volatility of daily log-ish returns."""
    if closes.empty:
        return pd.Series(dtype="float64")
    returns = closes.pct_change()
    return returns.rolling(window, min_periods=window).std() * (252 ** 0.5)


def relative_return(
    numerator: pd.Series, denominator: pd.Series, window: int = 20
) -> pd.Series:
    """Trailing return of one series minus another, aligned on shared dates.

    Used twice: equities against long treasuries (safe-haven demand) and
    junk against investment grade (junk-bond demand). Both are risk appetite
    measured by what the market is willing to hold.
    """
    if numerator.empty or denominator.empty:
        return pd.Series(dtype="float64")
    shared = numerator.index.intersection(denominator.index)
    if shared.empty:
        return pd.Series(dtype="float64")
    lhs = numerator.loc[shared].pct_change(window)
    rhs = denominator.loc[shared].pct_change(window)
    return lhs - rhs


@dataclass(frozen=True)
class FearGreed:
    """A composite reading and the components behind it.

    `components` holds only what could be computed. A missing input leaves its
    component out of both the dict and the average rather than defaulting it
    to 50, which would quietly pull every reading toward neutral.
    """

    date: pd.Timestamp
    score: float
    components: dict[str, float]
    missing: tuple[str, ...]

    @property
    def label(self) -> str:
        return label_for(self.score)

    def describe(self) -> str:
        parts = ", ".join(
            f"{name} {value:.0f}" for name, value in sorted(self.components.items())
        )
        text = f"{self.score:.0f}/100 — {self.label} ({parts})"
        if self.missing:
            text += f" [missing: {', '.join(self.missing)}]"
        return text


def fear_greed_frame(
    metrics: pd.DataFrame,
    *,
    benchmark: pd.Series | None = None,
    long_bond: pd.Series | None = None,
    junk: pd.Series | None = None,
    investment_grade: pd.Series | None = None,
) -> pd.DataFrame:
    """Per-date component scores and their composite.

    Every argument is optional because coverage is uneven and a partial index
    that says which parts are absent is more useful than one that refuses to
    compute or, worse, silently substitutes a neutral reading.
    """
    raw: dict[str, pd.Series] = {}

    if not metrics.empty:
        for name, series in (
            ("breadth", breadth_above_200(metrics)),
            ("price_strength", price_strength(metrics)),
            ("participation", participation(metrics)),
        ):
            if not series.empty:
                raw[name] = series

    if benchmark is not None and not benchmark.empty:
        momentum = momentum_vs_average(benchmark)
        if not momentum.dropna().empty:
            raw["momentum"] = momentum
        # Inverted: high volatility is the fear end, so rank the negative.
        volatility = realized_volatility(benchmark)
        if not volatility.dropna().empty:
            raw["volatility"] = -volatility

    if benchmark is not None and long_bond is not None:
        safe_haven = relative_return(benchmark, long_bond)
        if not safe_haven.dropna().empty:
            raw["safe_haven"] = safe_haven

    if junk is not None and investment_grade is not None:
        junk_demand = relative_return(junk, investment_grade)
        if not junk_demand.dropna().empty:
            raw["junk_demand"] = junk_demand

    if not raw:
        return pd.DataFrame(columns=[*COMPONENTS, "score"], dtype="float64")

    scored = pd.DataFrame(
        {name: trailing_percentile(series) for name, series in raw.items()}
    ).sort_index()
    scored["score"] = scored[list(raw)].mean(axis=1, skipna=True)
    return scored


def latest_reading(frame: pd.DataFrame) -> FearGreed | None:
    """The most recent date with a computable composite, or None."""
    if frame.empty or "score" not in frame.columns:
        return None
    usable = frame.dropna(subset=["score"])
    if usable.empty:
        return None

    row = usable.iloc[-1]
    present = {
        name: float(row[name])
        for name in COMPONENTS
        if name in usable.columns and pd.notna(row.get(name))
    }
    missing = tuple(name for name in COMPONENTS if name not in present)
    return FearGreed(
        date=usable.index[-1],
        score=float(row["score"]),
        components=present,
        missing=missing,
    )
