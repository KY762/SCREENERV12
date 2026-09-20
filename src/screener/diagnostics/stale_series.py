"""Find price series that keep trading after the company stopped existing.

`universe coverage` probes twelve hand-picked names. This checks every symbol
in the database against the provider's own list of what is no longer listed,
because the twelve were chosen when the problem was suspected, and the point
now is to find the cases nobody thought to name.

The failure it looks for, measured on EODHD on 2026-09-19:

    FRC    ends 2023-05-02   correct, First Republic failed that week
    SIVB   ends 2023-03-09   correct
    BBBY   runs to 2026-09   WRONG, bankrupt in 2023
    SBNY   runs to 2026-09   WRONG, Signature Bank failed in 2023

A dead company whose series continues is either a reused ticker -- a different
company now trading under those letters -- or a stale feed. Either way the
bars after the death are another company's, or nobody's, and a backtest that
holds "SBNY" through 2024 is holding something that did not exist.

This is worse than absence. A missing company is a gap that can be counted; a
company that quietly becomes a different one is a wrong number that looks
like a right one, and it survives every check that only asks whether data is
present.

The test is deliberately crude: delisted, yet still printing bars near the end
of the window. It cannot tell a reused ticker from a stale feed, and it does
not need to -- both make the tail unusable.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

# A delisted name whose last bar is within this of the data's end is still
# being printed. Generous on purpose: a company that delisted years ago and
# stops months before the end is a real, correctly truncated series.
RECENT_DAYS = 45


@dataclass(frozen=True)
class Series:
    """One symbol's extent in the database."""

    symbol: str
    first_bar: date
    last_bar: date
    bars: int


@dataclass(frozen=True)
class Suspect:
    symbol: str
    last_bar: date
    bars_after_delisting: int | None
    reason: str


def find_suspects(
    series: Iterable[Series],
    delisted: set[str],
    *,
    as_of: date,
    recent_days: int = RECENT_DAYS,
) -> list[Suspect]:
    """Series the provider calls delisted but is still quoting.

    `as_of` is the last date the data covers, not today: a database loaded
    last month should not report every symbol as stale.
    """
    cutoff = as_of - timedelta(days=recent_days)
    out = [
        Suspect(
            symbol=s.symbol,
            last_bar=s.last_bar,
            bars_after_delisting=None,
            reason=(
                f"listed as delisted, yet quoting to {s.last_bar} "
                f"({(as_of - s.last_bar).days} day(s) from the end of the data)"
            ),
        )
        for s in series
        if s.symbol in delisted and s.last_bar >= cutoff
    ]
    return sorted(out, key=lambda s: s.symbol)


def coverage_gap(wanted: Iterable[str], have: Iterable[str]) -> list[str]:
    """Symbols the universe needs and the database does not hold."""
    return sorted(set(wanted) - set(have))
