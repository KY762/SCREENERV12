"""SEC EDGAR — filing dates, used as an earnings-date proxy.

Why this exists
---------------
Post-earnings announcement drift is among the most replicated anomalies in the
literature, and it is the one well-documented effect available on daily bars
that the platform currently cannot test, because it has no earnings dates.

EDGAR is free, requires no key, and publishes every filing's acceptance
timestamp. No account, no rate-limit tier -- only a fair-access policy requiring
a descriptive User-Agent with a contact address, which SEC_USER_AGENT supplies.

What this is NOT
----------------
A filing date is not an announcement date. Companies typically issue results by
press release (Form 8-K) and file the 10-Q days later. The 8-K acceptance
timestamp is the closer proxy and is what this prefers; the periodic filing is
the fallback.

That gap is real and must be stated wherever these dates are used. A drift study
anchored on a date that lags the announcement measures a shorter, later window
than the literature does, which biases toward finding nothing. Biasing toward
nothing is the safe direction, but it is still a bias.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime

import httpx

from ..config import Settings, get_settings
from .base import ProviderError

log = logging.getLogger(__name__)

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
# Older filings do not live in the submissions document. See
# `older_submission_pages`.
OLDER_SUBMISSIONS_URL = "https://data.sec.gov/submissions/{name}"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# Balance-sheet and income tags needed for value and quality screens. Several
# concepts are reported under different tags by different registrants, so each
# entry is a fallback chain tried in order -- a single lookup silently returns
# nothing for perhaps a third of companies.
FACT_TAGS: dict[str, tuple[str, ...]] = {
    "assets": ("Assets",),
    "assets_current": ("AssetsCurrent",),
    "liabilities": ("Liabilities",),
    "liabilities_current": ("LiabilitiesCurrent",),
    "equity": (
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ),
    "cash": (
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ),
    "revenue": (
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ),
    "cost_of_revenue": ("CostOfRevenue", "CostOfGoodsAndServicesSold"),
    "gross_profit": ("GrossProfit",),
    "net_income": ("NetIncomeLoss",),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "long_term_debt": ("LongTermDebtNoncurrent", "LongTermDebt"),
    "shares_outstanding": (
        "CommonStockSharesOutstanding",
        "EntityCommonStockSharesOutstanding",
    ),
}

# Forms that carry results. 8-K is the press release; the rest are periodic.
EARNINGS_FORMS = ("8-K", "10-Q", "10-K")

# SEC fair access asks for no more than ten requests a second. One every
# 150ms is comfortably inside that and needs no coordination.
REQUEST_INTERVAL = 0.15


@dataclass(frozen=True)
class Fact:
    """One reported value, with the date it became public.

    ``filed`` is the load-bearing field. A period ends months before anyone can
    see the numbers, so a screen keyed on ``period_end`` is trading on
    information that did not exist. Every point-in-time query filters on
    ``filed``.
    """

    symbol: str
    concept: str          # our normalised name, e.g. "assets_current"
    tag: str              # the XBRL tag it actually came from
    unit: str
    period_end: date
    value: float
    filed: date
    accession: str
    form: str
    fiscal_year: int | None = None
    fiscal_period: str | None = None


@dataclass(frozen=True)
class Filing:
    symbol: str
    filed: date
    form: str
    period: date | None
    accession: str

    @property
    def is_press_release(self) -> bool:
        return self.form.startswith("8-K")


class EdgarProvider:
    """Filing dates by ticker. Read-only, keyless, politely rate-limited."""

    name = "edgar"

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self.settings = settings or get_settings()
        agent = (self.settings.sec_user_agent or "").strip()
        if not agent or "@" not in agent:
            raise ProviderError(
                "SEC_USER_AGENT must be set to a descriptive string containing a "
                "contact email, e.g. 'SCREENERV12 you@example.com'. EDGAR's fair "
                "access policy requires it and rejects requests without one."
            )
        self._client = client or httpx.Client(
            timeout=self.settings.request_timeout_seconds,
            headers={"User-Agent": agent, "Accept-Encoding": "gzip, deflate"},
            follow_redirects=True,
        )
        self._cik_cache: dict[str, str] | None = None
        self._last_request = 0.0

    # -- http ---------------------------------------------------------------

    def _get(self, url: str) -> dict:
        elapsed = time.monotonic() - self._last_request
        if elapsed < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - elapsed)
        try:
            response = self._client.get(url)
            self._last_request = time.monotonic()
            if response.status_code == 403:
                raise ProviderError(
                    "EDGAR returned 403. That is normally a User-Agent problem: "
                    "SEC_USER_AGENT must name the application and a contact email."
                )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"EDGAR rejected the request ({exc.response.status_code})"
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError(f"EDGAR unreachable: {exc}") from exc
        except ValueError as exc:
            raise ProviderError(f"EDGAR returned unparseable JSON: {exc}") from exc

    # -- lookup -------------------------------------------------------------

    def cik_for(self, ticker: str) -> str | None:
        """Zero-padded CIK for a ticker, or None if EDGAR does not list it.

        The map covers currently-listed registrants. A delisted company will be
        absent, which is itself worth knowing -- see 'screener universe
        coverage'.
        """
        if self._cik_cache is None:
            self._cik_cache = parse_ticker_map(self._get(TICKER_MAP_URL))
        return self._cik_cache.get(ticker.strip().upper())

    def get_filings(
        self, ticker: str, start: date, end: date, forms: tuple[str, ...] = EARNINGS_FORMS
    ) -> list[Filing]:
        cik = self.cik_for(ticker)
        if cik is None:
            raise ProviderError(f"EDGAR does not list a CIK for {ticker}")
        payload = self._get(SUBMISSIONS_URL.format(cik=cik))
        filings = parse_submissions(ticker, payload, forms)
        # `filings.recent` is not the filing history, only the newest page of
        # it. Anything older has to be fetched per page, or the early part of
        # the window comes back empty and reads as "this company filed
        # nothing" rather than "this provider did not look".
        for name in older_submission_pages(payload, start, end):
            filings.extend(
                parse_submissions(
                    ticker, self._get(OLDER_SUBMISSIONS_URL.format(name=name)), forms
                )
            )

        seen: set[str] = set()
        out: list[Filing] = []
        for filing in sorted(filings, key=lambda f: f.filed):
            if not start <= filing.filed <= end:
                continue
            # Pages are not documented as disjoint, and one filing counted
            # twice would look like two separate announcements.
            if filing.accession and filing.accession in seen:
                continue
            seen.add(filing.accession)
            out.append(filing)
        return out

    def get_company_facts(self, ticker: str) -> list[Fact]:
        """Every reported financial fact EDGAR holds for this registrant.

        One request per company, covering its entire filing history. The
        response is large -- tens of megabytes for an old filer -- which is why
        this is fetched once and stored rather than queried per screen.
        """
        cik = self.cik_for(ticker)
        if cik is None:
            raise ProviderError(f"EDGAR does not list a CIK for {ticker}")
        return parse_company_facts(ticker, self._get(COMPANY_FACTS_URL.format(cik=cik)))

    def get_earnings_dates(self, ticker: str, start: date, end: date) -> list[Filing]:
        """One filing per reporting period, preferring the 8-K press release.

        Companies file several 8-Ks per quarter for unrelated reasons, so this
        keeps the earliest filing per period rather than every 8-K -- the
        earliest is the one closest to the announcement.
        """
        filings = self.get_filings(ticker, start, end)
        return earliest_per_period(filings)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> EdgarProvider:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


# -- parsing helpers (pure, so the formats are pinned without a network) -----

def parse_ticker_map(payload: dict) -> dict[str, str]:
    """EDGAR's ticker file is a dict of positional records, not a list."""
    out: dict[str, str] = {}
    records = payload.values() if isinstance(payload, dict) else payload
    for record in records:
        try:
            ticker = str(record["ticker"]).upper()
            out[ticker] = str(record["cik_str"]).zfill(10)
        except (KeyError, TypeError, ValueError):
            continue
    return out


def parse_submissions(
    ticker: str, payload: dict, forms: tuple[str, ...] = EARNINGS_FORMS
) -> list[Filing]:
    """Parse a filings block, whether it is the recent one or an older page.

    EDGAR stores it column-wise -- parallel arrays rather than a list of
    records -- so the columns are zipped back together here.

    Two shapes arrive at this function. The submissions document nests the
    newest page under `filings.recent`; an older page is a bare document whose
    columns sit at the top level. Same columns either way.
    """
    payload = payload or {}
    block = ((payload.get("filings") or {}).get("recent")) or {}
    if not block and payload.get("filingDate"):
        block = payload

    filed = block.get("filingDate") or []
    form_types = block.get("form") or []
    periods = block.get("reportDate") or []
    accessions = block.get("accessionNumber") or []

    out: list[Filing] = []
    for i, form in enumerate(form_types):
        if not any(form.startswith(prefix) for prefix in forms):
            continue
        try:
            filed_on = date.fromisoformat(filed[i])
        except (IndexError, ValueError):
            continue
        period = None
        if i < len(periods) and periods[i]:
            try:
                period = date.fromisoformat(periods[i])
            except ValueError:
                period = None
        out.append(
            Filing(
                symbol=ticker.upper(),
                filed=filed_on,
                form=form,
                period=period,
                accession=accessions[i] if i < len(accessions) else "",
            )
        )
    return sorted(out, key=lambda f: f.filed)


def older_submission_pages(payload: dict, start: date, end: date) -> list[str]:
    """Names of the older filing pages whose range overlaps [start, end].

    `filings.recent` holds roughly the latest thousand filings of EVERY form,
    Form 4 insider reports included, so for an active large cap it can be only
    a couple of years deep. Everything before that is listed in
    `filings.files`, one entry per page, each declaring the range it covers.

    Reading only `recent` is silent rather than loud: the early part of a long
    window simply returns nothing, which is indistinguishable from a company
    that filed nothing. Measured on this universe on 2026-09-17 -- 10,391
    events ingested, but only 1,218 inside the 2010-2015 development split,
    across 92 of 271 symbols -- and h6's first battery run scored +0.203R on
    45 trades before anyone asked why there were only 45.

    Only overlapping pages are fetched; a page entirely outside the window is
    a request that buys nothing.
    """
    files = ((payload or {}).get("filings") or {}).get("files") or []
    names: list[str] = []
    for entry in files:
        try:
            name = str(entry["name"])
            covers_from = date.fromisoformat(entry["filingFrom"])
            covers_to = date.fromisoformat(entry["filingTo"])
        except (KeyError, TypeError, ValueError):
            # A page whose range will not parse is fetched rather than
            # skipped: missing filings is the failure that just cost a run.
            name = str(entry.get("name") or "").strip() if isinstance(entry, dict) else ""
            if name:
                names.append(name)
            continue
        if covers_to >= start and covers_from <= end:
            names.append(name)
    return names


def earliest_per_period(filings: list[Filing]) -> list[Filing]:
    """Collapse to one filing per reporting quarter.

    Two rules, in order:

    1. If ANY filing declares a reporting period, undated filings are dropped
       entirely. Companies file 8-Ks for many reasons -- a director resigning,
       a credit agreement, a restructuring -- and those carry no reportDate.
       Keeping them would scatter false events through the record, and for a
       drift study a mis-anchored event is worse than a missing one: it adds
       noise centred on nothing and dilutes whatever real effect exists.
    2. Among the remainder, one per quarter, earliest wins -- the 8-K press
       release precedes the 10-Q and sits closer to the announcement.

    Undated filings survive only for symbols where EDGAR supplies no report
    dates at all, where they are the only signal available.
    """
    dated = [f for f in filings if f.period is not None]
    usable = dated if dated else filings

    best: dict[tuple[int, int], Filing] = {}
    for filing in usable:
        anchor = filing.period or filing.filed
        key = (anchor.year, (anchor.month - 1) // 3)
        incumbent = best.get(key)
        if incumbent is None or filing.filed < incumbent.filed:
            best[key] = filing
    return sorted(best.values(), key=lambda f: f.filed)


def as_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def parse_company_facts(
    ticker: str, payload: dict, wanted: dict[str, tuple[str, ...]] | None = None
) -> list[Fact]:
    """Flatten EDGAR's companyfacts response.

    The structure is facts -> taxonomy -> tag -> units -> unit -> [records].
    Records for the same period appear MULTIPLE times, once per filing that
    reported it, which is how restatements are represented. All versions are
    kept: discarding them would make it impossible to reconstruct what was
    known at a past date, which is the entire point of storing this.
    """
    wanted = wanted or FACT_TAGS
    reverse: dict[str, str] = {}
    for concept, tags in wanted.items():
        for tag in tags:
            reverse.setdefault(tag, concept)

    facts_block = (payload or {}).get("facts") or {}
    out: list[Fact] = []

    for taxonomy, tags in facts_block.items():
        if taxonomy not in ("us-gaap", "dei"):
            continue
        for tag, body in (tags or {}).items():
            concept = reverse.get(tag)
            if concept is None:
                continue
            for unit, records in ((body or {}).get("units") or {}).items():
                for record in records or []:
                    fact = _parse_fact(ticker, concept, tag, unit, record)
                    if fact is not None:
                        out.append(fact)

    return sorted(out, key=lambda f: (f.concept, f.period_end, f.filed))


def _parse_fact(
    ticker: str, concept: str, tag: str, unit: str, record: dict
) -> Fact | None:
    try:
        end = date.fromisoformat(record["end"])
        filed = date.fromisoformat(record["filed"])
        value = float(record["val"])
    except (KeyError, TypeError, ValueError):
        return None
    return Fact(
        symbol=ticker.upper(),
        concept=concept,
        tag=tag,
        unit=unit,
        period_end=end,
        value=value,
        filed=filed,
        accession=str(record.get("accn") or ""),
        form=str(record.get("form") or ""),
        fiscal_year=record.get("fy") if isinstance(record.get("fy"), int) else None,
        fiscal_period=record.get("fp") or None,
    )
