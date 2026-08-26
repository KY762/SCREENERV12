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
        return [
            f for f in parse_submissions(ticker, payload, forms)
            if start <= f.filed <= end
        ]

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
    """Parse the recent-filings block.

    EDGAR stores it column-wise -- parallel arrays rather than a list of
    records -- so the columns are zipped back together here.
    """
    recent = ((payload or {}).get("filings") or {}).get("recent") or {}
    filed = recent.get("filingDate") or []
    form_types = recent.get("form") or []
    periods = recent.get("reportDate") or []
    accessions = recent.get("accessionNumber") or []

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
