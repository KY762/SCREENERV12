"""Symbols excluded from every universe, and why.

A backtest joins membership to prices by ticker, and tickers get reused. Where
the series we hold is not the company that was in the index, the choice is to
exclude it or to publish a number computed from the wrong company. This is the
exclusion, and the list is a committed file so that it is auditable: a symbol
disappears from the universe only if it appears here, with a reason and a date.

Scope, decided 2026-09-19 from `screener diagnose identity`, 24 symbols:

    EXCLUDED    10 that traded under $1M a day WHILE in the S&P 500, against a
                member median of $152M -- four of them at literally zero volume.
                12 whose letters now name an ETF or fund. 1 the vendor calls
                delisted while pricing it for another nine years (BBBY, whose
                2013-2015 closes are Overstock's). And 1 added by hand, BBT,
                which is Beacon Financial throughout and liquid enough to slip
                every rule. In all four cases the series covering the
                membership period is not that company's, so every trade drawn
                from it is fiction.

    NOT EXCLUDED  the 34 whose earlier history is simply ABSENT. Their series
                start after the ticker left the index, so there are no bars
                during the membership and nothing to get wrong. Excluding them
                would also remove the successor company's legitimate later
                membership -- DNB left in 2017 and Dun & Bradstreet Holdings
                listed again in 2020.

    ALSO NOT EXCLUDED  AVB, EA and EQR, which the delisted-flag rule DID flag
                before it was corrected. All three had just left the index,
                all three have correct continuous history, and EA's last closes
                are pinned at its take-private price. Quarantining a live
                company destroys clean data to prevent contamination that is
                not there, which is the mirror-image failure and just as bad.

This is coarser than it should be. The honest fix is to exclude a ticker only
for the dates where its identity conflicts, which needs the handover date, and
the vendor does not give one. Whole-symbol exclusion therefore also discards
periods that were fine. That costs coverage, which is the safe direction: a
missing company is a gap, and a wrong one is a wrong number.

What no rule covers is a ticker handed to another company of the same type that
is also liquid enough to pass the volume floor. BBT is the known case and it is
here by hand. Others are found by reading holder names and volumes together in
`screener diagnose identity`, and added the same way; a hand-entered row
carries a reason no rule emits and survives `--write`.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

# repository root / data / reference
QUARANTINE_FILE = (
    Path(__file__).resolve().parents[3] / "data" / "reference" / "universe_quarantine.csv"
)

# The reasons a rule can produce. Anything else in the file was put there by a
# person and survives a regeneration -- see `merge`.
GENERATED_REASONS = frozenset(
    {"too_illiquid_to_be_a_member", "not_a_stock", "outlived_its_security", "absent"}
)

# Of those, the ones that actually contaminate a backtest. "absent" is a gap,
# not a wrong number, and excluding it would cost a successor company's
# legitimate later membership -- see the module docstring.
CONTAMINATING_REASONS = frozenset(
    {"too_illiquid_to_be_a_member", "not_a_stock", "outlived_its_security"}
)


@dataclass(frozen=True)
class Excluded:
    symbol: str
    reason: str
    holder: str
    recorded_on: date
    detail: str


def load(path: Path | None = None) -> list[Excluded]:
    """Read the quarantine. A missing file excludes nothing, loudly enough:
    every caller reports the count it applied."""
    target = path or QUARANTINE_FILE
    if not target.exists():
        return []
    out: list[Excluded] = []
    with target.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            symbol = (row.get("symbol") or "").strip().upper()
            if not symbol:
                continue
            try:
                recorded = date.fromisoformat((row.get("recorded_on") or "").strip())
            except ValueError:
                recorded = date.min
            out.append(Excluded(
                symbol=symbol,
                reason=(row.get("reason") or "").strip(),
                holder=(row.get("holder") or "").strip(),
                recorded_on=recorded,
                detail=(row.get("detail") or "").strip(),
            ))
    return out


@lru_cache(maxsize=8)
def symbols(path: Path | None = None) -> frozenset[str]:
    """Just the tickers, for filtering membership.

    Cached: `universe_members` runs once per trading day, so a backtest asks
    thousands of times for a file that changes between runs and never during
    one. Anything that rewrites the file in-process calls `symbols.cache_clear`.
    """
    return frozenset(e.symbol for e in load(path))


def merge(generated: list[Excluded], existing: list[Excluded]) -> list[Excluded]:
    """Regeneration keeps hand-entered rows.

    The only way to catch a ticker handed to another company of the same type
    -- BBT, CPWR -- is for a person to read the holder name and add it. Those
    rows carry a reason no rule emits, and a `--write` that dropped them would
    silently un-quarantine the cases that needed a human to find. Where both
    sources name a symbol the hand-entered row wins, for the same reason.
    """
    by_hand = [e for e in existing if e.reason not in GENERATED_REASONS]
    claimed = {e.symbol for e in by_hand}
    return by_hand + [e for e in generated if e.symbol not in claimed]


def write(entries: list[Excluded], path: Path | None = None) -> Path:
    """Write the quarantine, sorted, so a regeneration produces a readable
    diff rather than a reshuffle."""
    target = path or QUARANTINE_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    symbols.cache_clear()
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["symbol", "reason", "holder", "recorded_on", "detail"]
        )
        writer.writeheader()
        for e in sorted(entries, key=lambda e: e.symbol):
            writer.writerow({
                "symbol": e.symbol,
                "reason": e.reason,
                "holder": e.holder,
                "recorded_on": e.recorded_on.isoformat(),
                "detail": e.detail,
            })
    return target
