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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True)
class Series:
    """One symbol's extent in the database."""

    symbol: str
    first_bar: date
    last_bar: date
    bars: int
    #: Median daily dollar volume over the symbol's membership window, where
    #: it is known. None means "not measured", which is not the same as thin.
    median_dollar_volume: float | None = None


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
    # "too_illiquid_to_be_a_member" | "not_a_stock" | "outlived_its_security"
    # | "absent"
    kind: str
    holder: str | None
    detail: str


#: An index member trading below this while IN the index is not that member.
#:
#: Measured 2026-09-19 over 798 symbols with 60+ bars inside their sp500_pit
#: membership: the median member trades $152M a day and the 5th percentile
#: $34.5M. This floor is 34x below that 5th percentile, so it cannot fire on a
#: thin-but-real constituent. Below it sit nine symbols -- AYE, RX, SII and
#: CPWR at literally zero volume, EP at $7/day, PARA at $32, ACS at $697, GR at
#: $7,140, KG at $68,372, GENZ at $338k -- every one of them a company acquired
#: or taken private between 2010 and 2012 whose letters a shell now holds.
#:
#: It deliberately stops short of BBBY ($1.68M) and BBT ($2.10M), which are
#: also contaminated but sit among names this check cannot separate from thin
#: real members. Those are caught by the rules below, or by hand.
MIN_MEMBER_DOLLAR_VOLUME = 1_000_000.0


def identity_conflicts(
    series: Iterable[Series],
    identity: dict[str, Identity],
    left_universe: dict[str, date],
    *,
    data_ends: date,
    still_trading_within_days: int = 45,
    outlived_after_days: int = 365,
    min_member_dollar_volume: float = MIN_MEMBER_DOLLAR_VOLUME,
) -> list[Conflict]:
    """Where the stored identity contradicts the stored prices.

    Four signals, in descending certainty. All are about members of the
    universe, because a ticker nobody traded on cannot corrupt a result.

    too_illiquid_to_be_a_member
                           the series traded less than a million dollars a day
                           WHILE the ticker was in the S&P 500. Membership
                           implies liquidity by construction -- the median
                           member trades $152M a day -- so this is not a
                           judgement about the company, it is arithmetic about
                           the index. It is the only check here that reads our
                           own prices rather than the vendor's metadata, which
                           is why it is first, and it is the only one that
                           catches a ticker handed to another company of the
                           same type: CPWR at zero volume is Ocean Thermal
                           Energy, not Compuware.

    not_a_stock            the letters now belong to an ETF or a fund. An
                           index member is a company, so the series that was
                           downloaded is not that company. FB is a ProShares
                           buffer ETF; EMC is a Global X emerging-markets ETF.
    outlived_its_security  the vendor's own list says this security is
                           delisted, yet the price series runs to the end of
                           the data AND has done so for a year or more since
                           the ticker left the index. The list and the prices
                           disagree, and a tail that long belongs to whoever
                           holds the letters now. BBBY is listed as Bed Bath &
                           Beyond and quotes into 2026 with Overstock's prices,
                           3,328 days after it left the index.

                           The year is what stops this firing on an ordinary
                           recent delisting, and it was added because the rule
                           without it flagged AVB, EA and EQR on 2026-09-19 --
                           all three had just left the index, all three had
                           correct continuous history, and EA's last closes
                           were pinned at its take-private price. Quarantining
                           them would have destroyed clean data on the strength
                           of a flag the paragraph below already calls
                           unreliable. Their tails were 9, 41 and 12 days; the
                           nearest true positive is 2,800. The threshold sits
                           in empty space, not in a crowd.
    absent                 the series starts after the ticker left the
                           universe, so the earlier company's history is
                           missing rather than wrong.

    What still cannot be settled from this data is the same-type handover that
    is ALSO liquid enough to pass the first check. BBT reads as "Beacon
    Financial Corporation" and traded a median $2.1M a day in the index -- ten
    times too little for BB&T, which was a top-50 US bank, but above a floor
    set where no real member can fall. Obvious to a person reading the name and
    the volume together, invisible to every rule here. That is why the names
    are reported.
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
        thin = (
            s.median_dollar_volume is not None
            and s.median_dollar_volume < min_member_dollar_volume
        )

        if thin:
            out.append(Conflict(
                symbol, "too_illiquid_to_be_a_member", holder,
                f"traded a median ${s.median_dollar_volume:,.0f} a day while in "
                f"the index, against a member median of $152M: whatever this "
                f"series is, it is not an S&P 500 constituent",
            ))
        elif ident and ident.security_type and ident.security_type != "Common Stock":
            out.append(Conflict(
                symbol, "not_a_stock", holder,
                f"an index member's ticker now refers to a {ident.security_type}",
            ))
        elif (
            ident
            and not ident.is_active
            and still_quoting
            and (s.last_bar - left).days >= outlived_after_days
        ):
            out.append(Conflict(
                symbol, "outlived_its_security", holder,
                f"listed as delisted, yet priced to {s.last_bar} -- "
                f"{(s.last_bar - left).days:,} days after it left on {left}",
            ))
        elif s.first_bar > left:
            out.append(Conflict(
                symbol, "absent", holder,
                f"series starts {s.first_bar}, after this ticker left on {left}",
            ))
    return out


# ---------------------------------------------------------------------------
# Superseded-instrument twins
# ---------------------------------------------------------------------------
#
# The checks above all read S&P 500 membership -- "too illiquid to be a member"
# is arithmetic about the index, and `left_universe` is an index date. The
# universe moved to 11,794 surveyed names on 2026-09-24 and there is no index
# membership for those, so none of it fires. This test is universe-independent.
#
# EODHD records a reused ticker by keeping the prior instrument under a
# suffixed code: JAVA_OLD is Sun Microsystems, JAVA is whoever holds the
# letters now. 1,845 such twins exist and 878 of them are tickers in the new
# candidate set, against a quarantine of 25 built for the old universe.
#
# The naive test -- does our stored series reach back before the twin stopped
# trading? -- flags 30% of them and is WRONG about a good share of those. GM is
# the counter-example: new GM listed in November 2010 while old GM's bankrupt
# shell still traded, so an overlap is expected and our series is correct.
#
# So this compares PRICES rather than dates. If our stored closes match the
# twin's closes on the days they share, our series IS the old company over that
# window and the ticker is contaminated. If they differ, they are two genuinely
# different securities and the overlap means nothing.

#: Closes within a tenth of a percent count as the same price. Not exact
#: equality: the two records can be rounded differently or adjusted at
#: different times, and demanding equality would report every contaminated
#: symbol as clean -- a false clean, which is the direction that costs most.
TWIN_PRICE_TOLERANCE = 0.001

#: Below this many shared days the comparison is noise either way.
TWIN_MIN_SHARED_DAYS = 5

#: Share of shared days that must match before the series is called the twin's.
TWIN_MIN_MATCH_RATE = 0.90


@dataclass(frozen=True)
class TwinOverlap:
    """One stored series judged against its superseded twin."""

    ticker: str
    twin: str
    shared_days: int
    matching_days: int
    verdict: str          # "contaminated" | "separate" | "insufficient"

    @property
    def match_rate(self) -> float:
        return self.matching_days / self.shared_days if self.shared_days else 0.0

    def describe(self) -> str:
        if self.verdict == "insufficient":
            return (
                f"{self.ticker}: only {self.shared_days} day(s) shared with "
                f"{self.twin}; not enough to judge"
            )
        return (
            f"{self.ticker}: {self.matching_days}/{self.shared_days} closes "
            f"({self.match_rate:.0%}) match {self.twin} -- {self.verdict}"
        )


def twin_overlap(
    ticker: str,
    twin: str,
    stored_closes: "pd.Series",
    twin_closes: "pd.Series",
    *,
    tolerance: float = TWIN_PRICE_TOLERANCE,
    min_shared_days: int = TWIN_MIN_SHARED_DAYS,
    min_match_rate: float = TWIN_MIN_MATCH_RATE,
) -> TwinOverlap:
    """Is our series for `ticker` actually the prices of `twin`?

    Both arguments are date-indexed closes. Only the dates they SHARE are
    compared; a twin that stopped trading before our series began shares
    nothing and is correctly reported as insufficient rather than clean.
    """
    import numpy as np

    shared = stored_closes.index.intersection(twin_closes.index)
    if len(shared) < min_shared_days:
        return TwinOverlap(ticker, twin, len(shared), 0, "insufficient")

    ours = stored_closes.loc[shared].to_numpy(dtype="float64")
    theirs = twin_closes.loc[shared].to_numpy(dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = np.abs(ours - theirs) / np.where(theirs == 0, np.nan, np.abs(theirs))
    matching = int(np.sum(np.isfinite(rel) & (rel <= tolerance)))

    rate = matching / len(shared)
    verdict = "contaminated" if rate >= min_match_rate else "separate"
    return TwinOverlap(ticker, twin, len(shared), matching, verdict)
