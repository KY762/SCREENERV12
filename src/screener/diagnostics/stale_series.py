"""Ticker identity: is this series the company we think it is?

A backtest joins membership to prices by TICKER. Tickers get reused, and a
vendor keys history to whoever holds the letters now, so a series can be a
different company from the one that was in the index -- with no gap, no jump,
and nothing that looks wrong.

Measured on this database, 2026-09-19, after loading EODHD:

    BBBY   2009-2026 continuous, and the 2013-2015 prices are OVERSTOCK's
           ($26, $15, $21) not Bed Bath & Beyond's ($60-80). Overstock
           renamed itself Bed Bath & Beyond Inc. and took the ticker.
    BBT    2009-2026 continuous, though BB&T merged into Truist in 2019
    CPWR   2009-2026 continuous, though Compuware went private in 2014
    EMC    starts 2023-05, so EMC Corp's own history (to its 2016 Dell
           acquisition) is absent
    BEAM   starts 2020-02: Beam Therapeutics, not the Beam Inc. that Suntory
           bought in 2014

Two failure modes, and they are not equally dangerous:

    ABSENT      the old company's history is missing and the series starts
                after it died. A backtest finds no data and the name drops
                out -- a gap, which can be counted.
    OVERWRITTEN a continuous series spanning two companies. Nothing looks
                wrong. This is the one that puts a false number in a result.

What this module does NOT do is decide which. Telling a reused ticker from a
company that merely shrank out of the index needs to know whether the original
company still exists, which is not in the price data. AAP, ANF and CLF all
left the index and still trade as themselves; EMC and BBT did not. So this
reports EVIDENCE and leaves the judgement with a person.

The real fix is to stop keying on tickers. A security identifier that survives
a rename -- ISIN, CUSIP, FIGI -- identifies the company rather than the
letters, and EODHD carries ISIN in its reference data. Recorded as an open
item rather than built here.

An earlier version of this module flagged "delisted, yet still quoting" as
contamination. It was wrong twice over: SBNY's shares really did keep trading
at fractions of a cent after the bank failed, which is a correct record, and
EODHD's delisted list also names live companies. Both were reported as
suspect. A check that cries wolf teaches the reader to skip the report.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Series:
    """One symbol's extent in the database."""

    symbol: str
    first_bar: date
    last_bar: date
    bars: int


@dataclass(frozen=True)
class IdentityRisk:
    """A ticker whose series may not be one company throughout."""

    symbol: str
    left_universe: date
    first_bar: date
    last_bar: date
    mode: str          # "absent" | "overwritten"
    detail: str


def identity_risks(
    series: Iterable[Series],
    left_universe: dict[str, date],
    *,
    data_ends: date,
    still_trading_within_days: int = 45,
) -> list[IdentityRisk]:
    """Tickers that left the universe long ago yet still quote today.

    `left_universe` is the last date each ticker was a member. A ticker that
    left and still trades is either the same company outside the index -- the
    common, innocent case -- or different letters' worth of company. Both are
    reported, with the evidence that separates them: whether the series covers
    the membership era.
    """
    by_symbol = {s.symbol: s for s in series}
    out: list[IdentityRisk] = []
    for symbol, left in sorted(left_universe.items()):
        s = by_symbol.get(symbol)
        if s is None:
            continue
        if (data_ends - s.last_bar).days > still_trading_within_days:
            continue                       # stopped trading; nothing to confuse
        if s.first_bar > left:
            out.append(IdentityRisk(
                symbol, left, s.first_bar, s.last_bar, "absent",
                f"series starts {s.first_bar}, after this ticker left the universe "
                f"on {left} -- the earlier company's history is missing",
            ))
        else:
            out.append(IdentityRisk(
                symbol, left, s.first_bar, s.last_bar, "overwritten",
                f"continuous {s.first_bar} to {s.last_bar}, spanning a membership "
                f"that ended {left} -- one series, possibly two companies",
            ))
    return out


@dataclass(frozen=True)
class Identity:
    """What a ticker refers to now, as recorded by `universe identify`."""

    symbol: str
    name: str | None
    security_type: str | None
    is_active: bool
    isin: str | None


@dataclass(frozen=True)
class Conflict:
    symbol: str
    kind: str          # "not_a_stock" | "outlived_its_security" | "absent"
    holder: str | None
    detail: str


def identity_conflicts(
    series: Iterable[Series],
    identity: dict[str, Identity],
    left_universe: dict[str, date],
    *,
    data_ends: date,
    still_trading_within_days: int = 45,
) -> list[Conflict]:
    """Where the stored identity contradicts the stored prices.

    Three signals, in descending certainty. All are about members of the
    universe, because a ticker nobody traded on cannot corrupt a result.

    not_a_stock            the letters now belong to an ETF or a fund. An
                           index member is a company, so the series that was
                           downloaded is not that company. FB is a ProShares
                           buffer ETF; EMC is a Global X emerging-markets ETF.
    outlived_its_security  the vendor's own list says this security is
                           delisted, yet the price series runs to the end of
                           the data. The list and the prices disagree, and the
                           tail belongs to whoever holds the letters now. BBBY
                           is listed as Bed Bath & Beyond and quotes into 2026
                           with Overstock's prices.
    absent                 the series starts after the ticker left the
                           universe, so the earlier company's history is
                           missing rather than wrong.

    A fourth case cannot be settled from this data: a ticker whose company
    quietly became another company of the same type, with the vendor listing
    only the newcomer. BBT reads as "Beacon Financial Corporation" and CPWR as
    "Ocean Thermal Energy Corp" -- obvious to a person reading the names, and
    invisible to any rule here. That is why the names are reported.
    """
    by_symbol = {s.symbol: s for s in series}
    out: list[Conflict] = []

    for symbol, left in sorted(left_universe.items()):
        s = by_symbol.get(symbol)
        if s is None:
            continue
        ident = identity.get(symbol)
        holder = ident.name if ident else None
        still_quoting = (data_ends - s.last_bar).days <= still_trading_within_days

        if ident and ident.security_type and ident.security_type != "Common Stock":
            out.append(Conflict(
                symbol, "not_a_stock", holder,
                f"an index member's ticker now refers to a {ident.security_type}",
            ))
        elif ident and not ident.is_active and still_quoting:
            out.append(Conflict(
                symbol, "outlived_its_security", holder,
                f"listed as delisted, yet priced to {s.last_bar}: the vendor's own "
                "list and its prices disagree",
            ))
        elif s.first_bar > left:
            out.append(Conflict(
                symbol, "absent", holder,
                f"series starts {s.first_bar}, after this ticker left on {left}",
            ))
    return out
