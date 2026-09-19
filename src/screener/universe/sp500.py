"""Point-in-time S&P 500 membership, from a free published dataset.

Operator decision, 2026-09-19: the universe becomes "the stocks that were in
the S&P 500 on each date" instead of 307 of today's large caps.

The old universe was chosen by who is large NOW, which is a survivorship
filter on the universe itself and not only on prices: a company that was in
the index in 2012 and shrank, failed or was bought is simply absent, and a
momentum rule is flattered by a universe pre-filtered to momentum that
persisted. Measured on 2026-09-19: 719 distinct companies were in the index
across 2010-2019, the database held bars for 106 of them, and 303 of the
missing are no longer in the index at all.

Source: github.com/fja05680/sp500, "S&P 500 Historical Components & Changes
(Updated).csv", MIT licence, vendored to data/reference/. One row per date
membership CHANGED, listing the full membership on that date.

What it is NOT: a vetted commercial dataset. It is maintained by hand against
Wikipedia, its author notes probable gaps before 2001, and it carries no
warranty. It is a large improvement on "today's large caps" and still wants
spot-checking against known index changes before any evidential run leans on
it. `definition_version` records the file it came from so a later correction
is visible as a change rather than a silent restatement.

MEASURED DEFECT, 2026-09-19: the symbols are not point-in-time even though the
membership is. Yahoo's 2010 membership is recorded as `AABA`, the ticker it
only took in 2017; `YHOO` appears nowhere. Seven of eight spot-checks passed
(FB in/out around Dec 2013, TSLA around Dec 2020, TWTR never a member) and
this was the eighth.

It matters because the symbol is how membership joins to price data. A company
whose ticker changed can silently fall out of the universe -- a gap created by
renaming rather than by survival, which is the `GPS` -> `GAP` problem this
project already hit once. Two things follow:

  - Whether it bites depends on the price vendor. Vendors that carry a
    company's whole history under its final ticker line up with this file;
    vendors that key on the historical ticker do not. Test EODHD on a renamed
    name before trusting a universe built here.
  - `symbol_aliases` exists for exactly this and is not yet wired to it.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db.models import Symbol, UniverseSnapshot

# The name this universe is stored and referenced under.
UNIVERSE_NAME = "sp500_pit"


@dataclass(frozen=True)
class Snapshot:
    """Membership as of a date on which it changed."""

    date: date
    tickers: tuple[str, ...]


@dataclass
class LoadResult:
    snapshots: int
    rows: int
    symbols_created: int
    first: date | None
    last: date | None

    def describe(self) -> str:
        span = f"{self.first} to {self.last}" if self.first else "nothing"
        return (
            f"{self.snapshots:,} snapshot(s), {self.rows:,} membership row(s), "
            f"{self.symbols_created:,} symbol(s) created, {span}"
        )


def parse(path: Path) -> list[Snapshot]:
    """Read the CSV into snapshots, oldest first.

    Tickers in the non-"Updated" edition of this file carry a delisting suffix
    (`AAMRQ-201312`). The suffix is stripped and the symbol kept: a company
    that left the index is exactly the kind this universe exists to include.
    """
    out: list[Snapshot] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            raw_date = (row.get("date") or "").strip()
            raw_tickers = (row.get("tickers") or "").strip()
            if not raw_date or not raw_tickers:
                continue
            try:
                day = date.fromisoformat(raw_date)
            except ValueError:
                continue
            tickers = tuple(sorted({
                t.strip().upper().split("-")[0]
                for t in raw_tickers.split(",")
                if t.strip()
            }))
            if tickers:
                out.append(Snapshot(day, tickers))
    out.sort(key=lambda s: s.date)
    return out


def load(
    session: Session,
    snapshots: list[Snapshot],
    *,
    name: str = UNIVERSE_NAME,
    version: str,
    start: date | None = None,
    end: date | None = None,
    replace: bool = True,
) -> LoadResult:
    """Write membership into `universe_snapshots`, creating missing symbols.

    A symbol row is created for every ticker, including ones with no price
    data: the point is to record that the company WAS in the universe then.
    What is missing afterwards is a measurable gap rather than an invisible
    one -- `screener universe coverage` is what measures it.

    `replace` clears this universe's existing rows first, so re-running after
    the source file updates restates it rather than layering two versions.
    """
    wanted = [
        s for s in snapshots
        if (start is None or s.date >= start) and (end is None or s.date <= end)
    ]
    if replace:
        session.execute(delete(UniverseSnapshot).where(UniverseSnapshot.name == name))

    known = {
        ticker: sid
        for ticker, sid in session.execute(select(Symbol.ticker, Symbol.id)).all()
    }
    created = 0
    for snapshot in wanted:
        for ticker in snapshot.tickers:
            if ticker not in known:
                symbol = Symbol(ticker=ticker, name=ticker, asset_type="equity")
                session.add(symbol)
                session.flush()
                known[ticker] = symbol.id
                created += 1

    rows = [
        {
            "name": name,
            "date": snapshot.date,
            "symbol_id": known[ticker],
            "definition_version": version,
        }
        for snapshot in wanted
        for ticker in snapshot.tickers
    ]
    if rows:
        session.bulk_insert_mappings(UniverseSnapshot, rows)

    return LoadResult(
        snapshots=len(wanted),
        rows=len(rows),
        symbols_created=created,
        first=wanted[0].date if wanted else None,
        last=wanted[-1].date if wanted else None,
    )
