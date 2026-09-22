"""Real bars with their predictability removed -- the null a strategy must fail.

Every bug in this project's log was invisible to a green test suite and surfaced
only on real data: a verification that compared zero rows, a target sitting on
the entry price, a hypothesis run under another hypothesis's exit rule. They
share a shape. The machinery produced a number, the number looked like a
result, and nothing in the pipeline was capable of saying "that cannot be
right".

This module builds the data that can say it. Each symbol's day-over-day returns
are permuted in time, carrying each day's intrabar geometry and volume with the
return that produced it. What survives: the marginal distribution of returns,
the drift, the fat tails, the bar shapes, the real trading calendar. What does
not: any relationship between a bar and the bars before it.

Nothing in a permuted series is predictable from its own past. A strategy that
still shows an edge on one is not measuring the market -- it is measuring the
machinery, and the finding is a bug report rather than a result.

Deliberately NOT geometric Brownian motion. Long-only strategies make money on
a series with positive drift whatever their selection rule, so a GBM null with
realistic drift passes everything and a zero-drift GBM tests against a market
that has never existed. Permutation keeps this universe's own drift and answers
the sharper question: given these returns, does the ORDER matter to us?
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("open", "high", "low", "close")


def permute_bars(frame: pd.DataFrame, *, seed: int = 0) -> pd.DataFrame:
    """One symbol's bars with the order of its returns destroyed.

    The index, the first close, and the multiset of log returns are preserved
    exactly. Each bar's open/high/low and volume travel with the return they
    belong to, so the joint distribution of (return, bar shape) survives and
    only the sequence changes.

    Frames too short to carry a return (fewer than three bars) come back
    unchanged: permuting one return is the identity, and silently returning
    something that looks shuffled but is not would make this check vacuous.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"bars are missing {', '.join(missing)}")

    if len(frame) < 3:
        return frame.copy()

    close = frame["close"].to_numpy(dtype="float64")
    if not np.all(np.isfinite(close)) or np.any(close <= 0):
        raise ValueError(
            "close must be finite and positive to permute returns; a "
            "non-positive price means the series is already wrong"
        )

    # Shape of each bar relative to its own close, so it can be re-attached to
    # a different price level without changing the bar's geometry. high >= low
    # and the open/close ordering are therefore preserved by construction.
    ratios = {
        column: frame[column].to_numpy(dtype="float64") / close
        for column in REQUIRED_COLUMNS
    }
    volume = (
        frame["volume"].to_numpy(dtype="float64")
        if "volume" in frame.columns
        else None
    )

    # Bar 0 anchors the series and has no return of its own, so only 1..n-1
    # take part. Log returns compose additively, which keeps the rebuilt series
    # free of the drift a naive simple-return rebuild introduces.
    log_returns = np.diff(np.log(close))
    order = np.random.default_rng(seed).permutation(len(log_returns))
    permuted = log_returns[order]

    rebuilt_close = np.empty_like(close)
    rebuilt_close[0] = close[0]
    rebuilt_close[1:] = close[0] * np.exp(np.cumsum(permuted))

    # Bar i>0 gets the geometry of the bar whose return it just inherited:
    # log_returns[k] is the move INTO bar k+1, so its shape lives at k+1.
    source = np.empty(len(close), dtype="int64")
    source[0] = 0
    source[1:] = order + 1

    out = pd.DataFrame(index=frame.index.copy())
    for column in REQUIRED_COLUMNS:
        out[column] = rebuilt_close * ratios[column][source]
    out["close"] = rebuilt_close
    if volume is not None:
        out["volume"] = volume[source]

    for column in frame.columns:
        if column not in out.columns:
            out[column] = frame[column].to_numpy()[source]

    return out[list(frame.columns)]


def permute_universe(
    bars_by_symbol: dict[str, pd.DataFrame], *, seed: int = 0
) -> dict[str, pd.DataFrame]:
    """Every symbol permuted under its own derived seed.

    A single shared permutation would move every symbol the same way on the
    same day, leaving the cross-section intact -- and the cross-section is
    exactly what H1 and H5 rank on. That null would be trivially passable by
    the strategies most in need of testing, which is worse than no null at all.

    Derived deterministically from `seed` and the ticker, so the whole universe
    reproduces from one integer.
    """
    out: dict[str, pd.DataFrame] = {}
    for ticker in sorted(bars_by_symbol):
        # Fixed width keeps this independent of Python's hash randomisation.
        derived = (seed * 1_000_003 + zlib_crc(ticker)) % (2**32)
        out[ticker] = permute_bars(bars_by_symbol[ticker], seed=derived)
    return out


def zlib_crc(text: str) -> int:
    """Stable across processes, unlike hash(). Named for what it is so nobody
    swaps in the builtin and reintroduces run-to-run drift."""
    import zlib

    return zlib.crc32(text.encode("utf-8"))
