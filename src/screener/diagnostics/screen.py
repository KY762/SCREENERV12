"""H8, the avoid screen: does leaving out a pool's most lottery-like names beat
drawing from all of it?

Every hypothesis before this one tried to PICK winners. Measured on CRSP
through July 2026 (the Obscura vault, `tools/long_legs.py`), no published
signal's buy side has beaten a random stock since 2005, while several AVOID
sides still lose to one: the most volatile fifth of small caps trailed a
random small cap by 0.91% a month (t -3.56). A long-only account cannot short
what is overpriced. It can decline to own it. Specification: docs/11.

The question is asked with no strategy in the way. On each date the expected
return of a random pick from a pool is the pool's mean, so the comparison is
the screened pool's mean against the full pool's, per date, over windows that
do not overlap. There is no exit rule, sizing or parameter to tune.

Trades follow the engine's own rules, so the numbers mean what a backtest's
would: fill at the next session's open, refused on a zero-volume bar; exit at
the open `horizon` sessions later, at the open of a zero-volume bar, or at the
close of a series' last bar. Cost is each name's own measured spread as of the
signal date (`calc/spread.spread_table`), one full spread per round trip.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from math import erfc, sqrt

import numpy as np
import pandas as pd

from ..backtest.splits import REGIMES, Split

#: The pool's top fifth on the date is left out, as the literature sorts it.
SCREEN_QUANTILE = 0.80
#: Sessions of daily returns behind each screen variable.
VOL_WINDOW = 60
MAX_WINDOW = 21
#: Development only. Validation and test are budgeted against the database
#: (non-negotiable 5) and this diagnostic keeps no budget, so it refuses them.
ALLOWED_SPLITS = ("development",)


@dataclass(frozen=True)
class Window:
    day: date
    names: int
    pool_gross: float
    pool_net: float
    kept_gross: float
    kept_net: float
    kept_trimmed: float
    pool_trimmed: float
    out_median: float
    pool_median: float
    share_out: float


def screen_variables(bars: pd.DataFrame) -> pd.DataFrame:
    """vol60 and max21 for one series, stamped on the day they are known."""
    r = bars["close"].astype("float64").pct_change()
    return pd.DataFrame({
        "vol60": r.rolling(VOL_WINDOW, min_periods=40).std(),
        "max21": r.rolling(MAX_WINDOW, min_periods=15).max(),
    })


def trade_return(bars: pd.DataFrame, i: int, horizon: int) -> float | None:
    """The engine's round trip for a signal on bar ``i``, before costs."""
    n = len(bars)
    if i + 1 >= n:
        return None
    opens = bars["open"].to_numpy(dtype="float64")
    vol = bars["volume"].to_numpy(dtype="float64") if "volume" in bars else np.ones(n)
    if vol[i + 1] <= 0 or not opens[i + 1] > 0:
        return None                              # no fill on a bar nobody traded
    entry = opens[i + 1]
    for j in range(i + 2, min(n, i + 2 + horizon)):
        if vol[j] <= 0:
            return opens[j] / entry - 1.0        # no_volume exit
    if i + 1 + horizon < n:
        return opens[i + 1 + horizon] / entry - 1.0
    return float(bars["close"].iloc[-1]) / entry - 1.0   # series_end exit


def _trimmed(x: np.ndarray, cut: float = 0.10) -> float:
    x = np.sort(x)
    k = int(len(x) * cut)
    return float(x[k:len(x) - k].mean()) if len(x) > 10 else float("nan")


def measure(
    bars_by_symbol: dict[str, pd.DataFrame],
    *,
    split: Split,
    eligible: Callable[[str, date], bool],
    spreads: dict[str, pd.Series],
    horizon: int = 20,
    stride: int = 20,
) -> list[Window]:
    """One Window per signal date, `stride` sessions apart."""
    if split.name not in ALLOWED_SPLITS:
        raise ValueError(
            f"H8 is measured on {ALLOWED_SPLITS} only; {split.name} is budgeted "
            "and needs a signed pre-registration and budget accounting first (docs/11)"
        )
    calendar = sorted({d for f in bars_by_symbol.values() for d in f.index
                       if split.start <= d.date() <= split.end})[::stride]
    wanted = set(calendar)
    rows: dict[pd.Timestamp, list[tuple[float, float, float, float]]] = {d: [] for d in calendar}
    for key, bars in bars_by_symbol.items():
        if len(bars) < VOL_WINDOW + 2:
            continue
        variables = screen_variables(bars)
        spread = spreads.get(key)
        for i in np.flatnonzero(bars.index.isin(wanted)):
            stamp = bars.index[i]
            if not eligible(key, stamp.date()):
                continue
            v, m = variables.iloc[i]
            if pd.isna(v) or pd.isna(m):
                continue
            ret = trade_return(bars, int(i), horizon)
            if ret is None:
                continue
            cost = float(spread.get(stamp, np.nan)) if spread is not None else float("nan")
            rows[stamp].append((float(v), float(m), ret, cost))

    out = []
    for stamp in calendar:
        got = rows[stamp]
        if len(got) < 50:
            continue
        a = np.asarray(got, dtype="float64")
        vol, mx, ret, cost = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
        # A name with no spread estimate yet is charged the date's median; a
        # date with none at all (tests, or a pool too new) is charged nothing.
        if np.isnan(cost).all():
            cost = np.zeros_like(cost)
        else:
            cost = np.where(np.isnan(cost), np.nanmedian(cost), cost)
        net = ret - cost
        out_mask = ((vol >= np.quantile(vol, SCREEN_QUANTILE))
                    | (mx >= np.quantile(mx, SCREEN_QUANTILE)))
        keep = ~out_mask
        out.append(Window(
            day=stamp.date(), names=len(ret),
            pool_gross=float(ret.mean()), pool_net=float(net.mean()),
            kept_gross=float(ret[keep].mean()), kept_net=float(net[keep].mean()),
            kept_trimmed=_trimmed(ret[keep]), pool_trimmed=_trimmed(ret),
            out_median=float(np.median(ret[out_mask])), pool_median=float(np.median(ret)),
            share_out=float(out_mask.mean()),
        ))
    return out


@dataclass(frozen=True)
class Verdict:
    windows: int
    mean_net: float
    t_net: float
    p_net: float
    mean_gross: float
    t_gross: float
    mean_trimmed: float
    regimes_positive: int
    regimes_total: int
    by_regime: dict[str, tuple[int, float]]

    @property
    def passes_development(self) -> bool:
        """docs/11 section 4: net p <= 0.05 one-sided, positive in >= 2 of the
        split's regime buckets, and the trimmed version positive too."""
        return (self.p_net <= 0.05 and self.regimes_positive >= 2
                and self.mean_trimmed > 0)


def _t(x: np.ndarray) -> float:
    return float(x.mean() / (x.std(ddof=1) / sqrt(len(x)))) if len(x) > 2 else float("nan")


def judge(windows: list[Window], split: Split) -> Verdict:
    net = np.array([w.kept_net - w.pool_net for w in windows])
    gross = np.array([w.kept_gross - w.pool_gross for w in windows])
    trimmed = np.array([w.kept_trimmed - w.pool_trimmed for w in windows])
    t_net = _t(net)
    by_regime = {}
    for regime in REGIMES:
        if not (split.start <= regime.start <= split.end):
            continue
        sel = np.array([w.kept_net - w.pool_net for w in windows
                        if regime.start <= w.day <= regime.end])
        by_regime[regime.name] = (len(sel), float(sel.mean()) if len(sel) else float("nan"))
    positive = sum(1 for n, m in by_regime.values() if n and m > 0)
    return Verdict(
        windows=len(net), mean_net=float(net.mean()), t_net=t_net,
        p_net=0.5 * erfc(t_net / sqrt(2)), mean_gross=float(gross.mean()),
        t_gross=_t(gross), mean_trimmed=float(np.nanmean(trimmed)),
        regimes_positive=positive, regimes_total=len(by_regime), by_regime=by_regime,
    )
