"""A long hole in trading ends a series.

A vendor keys history to whoever holds the letters now, so a ticker that
changed hands is stored as ONE series: the old company's prices, a hole while
nobody held the ticker, then the new holder's prices. JAVA is Sun Microsystems
until 2010-01-26, nothing for eleven years, then a JPMorgan ETF from 2021.
Every rolling window computed across that hole compares two securities, and a
position open on the last Sun bar is next priced on the ETF.

Measured 2026-09-24 on 11,868 stored symbols: 801 carry a hole of 60+ days
between traded bars (volume > 0), 483 of 180+. The `_OLD` twin scan in
`diagnostics/stale_series.py` sees about 25 of them -- only where the vendor
happened to keep a record of the prior holder. The hole needs no vendor
metadata at all.

The rule cuts rather than quarantines. Each side of the hole is a real record
of a real security -- JAVA before 2010 really is Sun's prices -- so both are
kept, as separate series. Whole-symbol quarantine discards both.

The threshold is the operator's (2026-09-24): 60 days catches every confirmed
handover found that night except one bankruptcy re-listing (OAS, 42 days), and
leaves ordinary trading halts of the same company as one series.

Zero-volume placeholder bars inside a hole belong to the series BEFORE it:
they are the frozen tail of the security that stopped, and the engine's
`no_volume` exit depends on seeing them.
"""

from __future__ import annotations

import pandas as pd

#: Calendar days between two traded bars that end one series and start another.
MAX_GAP_DAYS = 60

#: Separates a ticker from the last traded date of an earlier series:
#: ``JAVA@2010-01-26`` is the JAVA that stopped trading on that day. The latest
#: series keeps the bare ticker, because that is the security a live screen or
#: a forward test sees today.
SEGMENT_MARK = "@"


def split_at_gaps(
    frame: pd.DataFrame, max_gap_days: int = MAX_GAP_DAYS
) -> list[pd.DataFrame]:
    """Cut ``frame`` wherever two traded bars sit ``max_gap_days`` or more apart.

    A bar is traded when its volume is positive, or when the frame carries no
    volume column at all. Returns the pieces oldest first; a frame with no such
    hole comes back whole, as the only element.
    """
    if frame.empty:
        return [frame]
    if "volume" in frame.columns:
        traded = frame.index[frame["volume"].astype(float) > 0]
    else:
        traded = frame.index
    if len(traded) < 2:
        return [frame]

    gaps = traded[1:] - traded[:-1]
    starts = traded[1:][gaps >= pd.Timedelta(days=max_gap_days)]
    if len(starts) == 0:
        return [frame]

    pieces = []
    lower = None
    for start in starts:
        piece = frame[frame.index < start] if lower is None else frame[
            (frame.index >= lower) & (frame.index < start)
        ]
        pieces.append(piece)
        lower = start
    pieces.append(frame[frame.index >= lower])
    return [p for p in pieces if not p.empty]


def segment_keys(ticker: str, pieces: list[pd.DataFrame]) -> list[str]:
    """Names for the pieces ``split_at_gaps`` returned, in the same order.

    The last piece keeps ``ticker``. Each earlier one is named for the last day
    it TRADED, not its last row, so a frozen zero-volume tail does not move the
    name off the date the security actually stopped.
    """
    keys = []
    for i, piece in enumerate(pieces):
        if i == len(pieces) - 1:
            keys.append(ticker)
            continue
        if "volume" in piece.columns:
            traded = piece.index[piece["volume"].astype(float) > 0]
        else:
            traded = piece.index
        last = traded[-1] if len(traded) else piece.index[-1]
        keys.append(f"{ticker}{SEGMENT_MARK}{last:%Y-%m-%d}")
    return keys


def base_ticker(key: str) -> str:
    """The ticker a series key belongs to: ``JAVA@2010-01-26`` -> ``JAVA``.

    Anything keyed by ticker and dated -- index membership, earnings dates --
    applies to whichever series was trading on the date, and series from one
    ticker never overlap, so stripping the mark is enough to look them up.
    """
    return key.split(SEGMENT_MARK, 1)[0]
