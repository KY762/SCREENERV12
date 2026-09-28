"""Bars no security can print, and what each kind does to a series.

Measured 2026-09-28 on the development window of every series that passes
through `swing_small_mid`: 383 series carried bars that a split-adjusted
price record cannot contain. SCU goes x100 in price and /100 in volume on
2014-12-16. TRA goes from $41 to $14,797. NLCS has zero-volume bars near
$1,100 between traded bars near $28, and the engine's `no_volume` exit fills
at such a bar's open. They touched 0.42% of name-dates and moved a random
pick's mean 20-session return from +0.54% to +1.01%: an average over the pool
was mostly an average of these.

Four kinds, each handled the way the evidence for it allows:

    zero-volume bar priced away    Nothing traded, so the bar has no price of
                                   its own. Its OHLC becomes the last traded
                                   close. The bar is kept, because the
                                   `no_volume` exit depends on seeing it; it
                                   now exits at the last price anyone paid.
    spike that reverts             A one-day move past 3x or below 1/3 that
                                   comes back within five traded bars. No
                                   listed stock triples and untriples in a
                                   week; the bars in between are dropped.
    certain break                  A one-day move to 5x or more, to a tenth
                                   or less, by a power of ten, or reversed by
                                   a counter-move within 400 days. The series
                                   is CUT there, like the 60-day gap rule:
                                   each side is a coherent record, and no
                                   return spans the join.
    a 3x-5x rise on falling share  The signature of an unrecorded reverse
    volume                         split. Cut.

What is NOT touched, deliberately: a one-day fall to between a third and a
tenth of the prior close that nothing else explains. Clovis fell 70% on
2015-11-16 and Medivation 67% on 2010-03-03, and those were real. Cutting
there would let a position exit at the prior close and escape a real loss,
which is ambiguity resolved in the strategy's favour (non-negotiable 6). A
3x-5x rise on normal volume stays too: Intercept went x3.8 on 2014-01-09.

This uses later bars to decide that earlier ones were errors. That is
hindsight about the DATA, not about the market -- no order could have filled
at a price nobody traded -- and it is the same kind of hindsight the 60-day
gap rule already uses. It is applied to history for research. A live screen
meeting a garbage bar today sees a certain break and a one-bar series, which
it cannot trade, and that is the safe failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

#: A one-day move beyond this factor, either way, is not an ordinary move.
JUMP = 3.0
#: A jump that comes back within this many traded bars is a spike.
REVERT_BARS = 5
#: "Comes back" means to within this factor of the close before the jump.
REVERT_BAND = 1.5
#: One-day rises of this factor or more are breaks whatever else is true.
CERTAIN_UP = 5.0
#: One-day falls to this fraction or less are breaks whatever else is true.
CERTAIN_DOWN = 0.1
#: Within this factor of a power of ten: a unit or split error.
SCALE_TOLERANCE = 1.06
#: A counter-move of the inverse size within this many days pairs two jumps.
PAIR_DAYS = 400
PAIR_BAND = 1.3
#: A 3x-5x rise with share volume falling to this fraction is a reverse split.
REVERSE_SPLIT_VOLUME = 0.5
VOLUME_WINDOW = 20
#: A zero-volume bar further than this factor from the last traded close.
ZERO_VOLUME_BAND = 1.5


@dataclass
class Repair:
    """What `repair` changed in one series."""

    repriced: list[pd.Timestamp] = field(default_factory=list)
    dropped: list[pd.Timestamp] = field(default_factory=list)
    cuts: list[pd.Timestamp] = field(default_factory=list)
    kept: list[pd.Timestamp] = field(default_factory=list)   # impossible-looking, left alone

    @property
    def touched(self) -> bool:
        return bool(self.repriced or self.dropped or self.cuts)


def _traded(frame: pd.DataFrame) -> np.ndarray:
    if "volume" not in frame.columns:
        return np.ones(len(frame), dtype=bool)
    return frame["volume"].to_numpy(dtype="float64") > 0


def _reprice_zero_volume(frame: pd.DataFrame, report: Repair) -> pd.DataFrame:
    traded = _traded(frame)
    if traded.all():
        return frame
    close = frame["close"].to_numpy(dtype="float64")
    opens = frame["open"].to_numpy(dtype="float64")
    out = frame.copy()
    last = np.nan
    band = np.log(ZERO_VOLUME_BAND)
    cols = [c for c in ("open", "high", "low", "close") if c in out.columns]
    for i in range(len(frame)):
        if traded[i]:
            last = close[i]
            continue
        if not np.isfinite(last) or last <= 0:
            continue
        o, c = opens[i], close[i]
        off = (not (o > 0 and c > 0)) or max(abs(np.log(o / last)), abs(np.log(c / last))) > band
        if off:
            out.iloc[i, [out.columns.get_loc(k) for k in cols]] = last
            report.repriced.append(frame.index[i])
    return out


def _jumps(frame: pd.DataFrame) -> list[tuple[int, int, float]]:
    """(position, position of the prior traded bar, ratio) for every traded bar
    whose close is beyond JUMP of the previous traded close."""
    traded = _traded(frame)
    close = frame["close"].to_numpy(dtype="float64")
    out = []
    prev = -1
    for i in range(len(frame)):
        if not traded[i]:
            continue
        if prev >= 0 and close[prev] > 0 and close[i] > 0:
            r = close[i] / close[prev]
            if r > JUMP or r < 1.0 / JUMP:
                out.append((i, prev, r))
        prev = i
    return out


def _drop_spikes(frame: pd.DataFrame, report: Repair) -> pd.DataFrame:
    """Drop excursions that come back within REVERT_BARS traded bars."""
    # Removing one excursion can expose another beside it, so repeat until a
    # pass finds none. Each pass takes every non-overlapping excursion at once.
    for _ in range(20):
        traded = _traded(frame)
        close = frame["close"].to_numpy(dtype="float64")
        drop: list[int] = []
        covered = -1
        for i, prev, _r in _jumps(frame):
            if i <= covered:
                continue
            base = close[prev]
            seen, k = 0, i + 1
            while k < len(frame) and seen < REVERT_BARS:
                if traded[k]:
                    seen += 1
                    if close[k] > 0 and abs(np.log(close[k] / base)) < np.log(REVERT_BAND):
                        drop.extend(range(i, k))
                        covered = k
                        break
                k += 1
        if not drop:
            return frame
        report.dropped.extend(frame.index[drop])
        frame = frame.drop(index=frame.index[drop])
    return frame


def _is_scale(r: float) -> bool:
    lr = np.log10(r)
    nearest = round(lr)
    return nearest != 0 and abs(lr - nearest) < np.log10(SCALE_TOLERANCE)


def _breaks(frame: pd.DataFrame, report: Repair) -> list[pd.Timestamp]:
    jumps = _jumps(frame)
    if not jumps:
        return []
    traded = _traded(frame)
    volume = frame["volume"].to_numpy(dtype="float64") if "volume" in frame else None
    dates = frame.index
    paired = [False] * len(jumps)
    for a in range(len(jumps)):
        for b in range(a + 1, len(jumps)):
            if (dates[jumps[b][0]] - dates[jumps[a][0]]).days > PAIR_DAYS:
                break
            if abs(np.log(jumps[a][2] * jumps[b][2])) < np.log(PAIR_BAND):
                paired[a] = paired[b] = True
    cuts = []
    for (i, _prev, r), pair in zip(jumps, paired, strict=True):
        cut = r >= CERTAIN_UP or r <= CERTAIN_DOWN or _is_scale(r) or pair
        if not cut and r > JUMP and volume is not None:
            before = volume[max(0, i - VOLUME_WINDOW):i][traded[max(0, i - VOLUME_WINDOW):i]]
            after = volume[i:i + VOLUME_WINDOW][traded[i:i + VOLUME_WINDOW]]
            if len(before) and len(after) and np.median(before) > 0:
                cut = np.median(after) / np.median(before) < REVERSE_SPLIT_VOLUME
        if cut:
            cuts.append(dates[i])
        else:
            report.kept.append(dates[i])
    return cuts


def repair(frame: pd.DataFrame) -> tuple[pd.DataFrame, Repair]:
    """Reprice, drop and find the cut points. Returns the frame and a report;
    `split_at_breaks` applies the cuts."""
    report = Repair()
    if frame.empty or "close" not in frame.columns or len(frame) < 2:
        return frame, report
    frame = _reprice_zero_volume(frame, report)
    frame = _drop_spikes(frame, report)
    report.cuts = _breaks(frame, report)
    return frame, report


def split_at_breaks(frame: pd.DataFrame, cuts: list[pd.Timestamp]) -> list[pd.DataFrame]:
    """Cut ``frame`` so each date in ``cuts`` starts a new piece."""
    if not cuts:
        return [frame]
    pieces, lower = [], None
    for start in sorted(cuts):
        if lower is None:
            mask = frame.index < start
        else:
            mask = (frame.index >= lower) & (frame.index < start)
        pieces.append(frame[mask])
        lower = start
    pieces.append(frame[frame.index >= lower])
    return [p for p in pieces if not p.empty]


def clean_pieces(frame: pd.DataFrame) -> tuple[list[pd.DataFrame], Repair]:
    """The series a stored symbol really is: cut at 60-day holes, then each
    piece repaired and cut at its breaks. Holes first, so a repair never
    compares two different securities. Returns the pieces oldest first and
    one combined report."""
    from .segments import split_at_gaps

    total = Repair()
    pieces: list[pd.DataFrame] = []
    for piece in split_at_gaps(frame):
        fixed, report = repair(piece)
        total.repriced.extend(report.repriced)
        total.dropped.extend(report.dropped)
        total.cuts.extend(report.cuts)
        total.kept.extend(report.kept)
        pieces.extend(split_at_breaks(fixed, report.cuts))
    return pieces, total
