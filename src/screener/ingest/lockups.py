"""IPO lock-up expiry dates, extracted from SEC EDGAR prospectuses.

Why this exists
----------------
H9 (``preregistrations/H9.md``) tests Field & Hanka (2001): a roughly -1.5%
three-day abnormal return at IPO lock-up expiry, larger for VC-backed firms.
Testing it needs an actual expiry date per IPO. No free structured dataset
gives one -- Jay Ritter's IPO data (site.warrington.ufl.edu/ritter) was
checked 2026-10-03 and lists offer dates, prices and first-day returns, but
no lock-up terms. The date has to come from the prospectus itself, which
states the lock-up length in days as a matter of disclosure under
"Underwriting."

IDENTIFICATION, not just extraction, is the hard part
-------------------------------------------------------
``EdgarProvider.cik_for`` resolves a ticker through EDGAR's CURRENT
ticker-to-CIK map (``company_tickers.json``) -- a snapshot of who EDGAR
thinks trades under a ticker *today*. Measured 2026-10-03 against this
project's own database: of 1,625 symbols whose first stored bar falls in
2010-02-01..2015-06-30 (candidate new listings), only 635 (39%) are still
trading under the same ticker as of 2026-08. ``cik_for`` returns ``None``
for the rest -- or, worse, if the ticker was later reused (the JAVA problem,
see ``CLAUDE.md`` "A hole in trading ends a series"), it can return the CIK
of an unrelated, *current* company holding the same letters, silently.

Two fixes were needed, found in that order. ``EdgarCompanySearch`` first
searched EDGAR's full historical registrant-name index
(``browse-edgar?action=getcompany``), which finds a filer whether or not it
still exists today -- confirmed 2026-10-03 against Textura Corp (TXTR,
IPO'd June 2013, acquired and delisted 2016): absent from the current
ticker map, found correctly by name. **That still was not enough.** A
15-candidate pilot run found this project's own ``symbols.name`` column
empty for 13 of 15 -- it is populated for only 1,050 of 11,868 stored
symbols, essentially the original EODHD load, not the 2026-09-24 expansion
most of this window's candidates come from. Searching by name cannot work
on a name that was never stored.

The fix is to search EDGAR's FULL TEXT index (``efts.sec.gov``) for the
ticker itself, as a quoted phrase, inside the 424B family of final-
prospectus filings near the candidate's first bar. A prospectus states its
own ticker on the cover
page and again throughout "Underwriting", so this needs nothing from our
own database but the ticker and an approximate date -- it does not depend
on ``name`` at all, and so is not exposed to the same gap. Confirmed
2026-10-03 against Ironwood Pharmaceuticals (IRWD, 2010-02-04 424B4, name
also absent from this database): one exact hit, by ticker and date alone.

Construction method
--------------------
1. Candidates: symbols whose first stored bar falls in the requested
   window, read from this project's own ``symbols`` table (point-in-time:
   that row's ``first_date`` is literally the first bar ever ingested for
   the ticker).
2. For each, search EDGAR's full text index for the ticker, quoted, inside
   424B1-424B5 filings (whichever Rule 424(b) paragraph the IPO's final
   prospectus used) filed within :data:`TICKER_SEARCH_WINDOW_DAYS` of the
   candidate's first bar. More than one distinct company matching is
   excluded and counted -- not guessed at.
3. The filing's cover page must state the SAME ticker as the candidate's.
   This is the collision check for a ticker that is also an ordinary word
   or abbreviation appearing in an unrelated filing by coincidence.
4. The lock-up length is read from the "Lock-Up Agreement" clause itself
   (see ``extract_lockup_days``), not assumed to be 180 days. A filing
   where that clause cannot be found, or where it is not unambiguous, is
   excluded and counted, not defaulted.
5. Expiry = filing date + N calendar days. The filing date is what the
   clause itself counts from ("the date of this prospectus"), so no
   separate IPO-date concept is needed.

``filings_by_name``/``search_prefix`` (the first attempt) are kept: they
still work when a name IS stored, and are exercised by their own tests, but
``build_lockup_table`` no longer depends on them being available.

What this does not capture: the "booster shot" extension many underwriting
agreements include (FINRA Rule 2241-style), which pushes the lock-up out if
an earnings release or material announcement falls in roughly its last 17
days. Found for real in the module's own worked example (Textura Corp,
2013-06-06 424B4). The expiry date used here is the CONTRACTUAL BASE date,
which for an affected IPO is a few days early -- early is the direction
that understates rather than invents an effect.
"""

from __future__ import annotations

import html
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from xml.etree import ElementTree as ET

import httpx

from ..config import Settings, get_settings
from ..providers.base import ProviderError

log = logging.getLogger(__name__)

_ATOM_NS = "{http://www.w3.org/2005/Atom}"
BROWSE_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
FTS_URL = "https://efts.sec.gov/LATEST/search-index"

#: Window, either side of a candidate's first stored bar, that full text
#: search is restricted to when looking for its IPO prospectus by ticker.
#: Tight enough that an unrelated filing using the same letters as an
#: ordinary word or a different company's ticker, months away, cannot
#: match; wide enough to absorb the few trading days between a prospectus
#: being filed and the first bar this project actually has for it.
TICKER_SEARCH_WINDOW_DAYS = 15

#: The final-prospectus forms a firm-commitment IPO is filed under. 424B4
#: is the overwhelming majority; the rest cover the other Rule 424(b)
#: paragraphs issuers use depending on how the offering was priced.
#: Measured 2026-10-03: restricting to 424B4/424B5 alone missed Terreno
#: Realty's 2010-02 IPO (TRNO), filed as 424B1 -- a real, findable IPO that
#: a narrower list would have reported as "no filing found," silently
#: understating how much of the universe is actually confirmable.
IPO_PROSPECTUS_FORMS: tuple[str, ...] = ("424B1", "424B2", "424B3", "424B4", "424B5")

#: Same fair-access pacing as ``providers/edgar.py`` -- SEC asks for no more
#: than ten requests a second.
REQUEST_INTERVAL = 0.15

_SEARCH_WORD_RE = re.compile(r"[A-Za-z0-9&]+")
_GENERIC_FIRST_WORDS = frozenset({
    "the", "american", "national", "united", "first", "global", "international",
    "new", "us", "america", "general", "pacific", "atlantic",
})

_LOCKUP_SECTION_RE = re.compile(r"lock[\s-]?up\s+agreements?", re.IGNORECASE)
_RULE144_RE = re.compile(r"rule\s*144", re.IGNORECASE)
_DAY_RE = re.compile(r"(\d{2,3})\s*-?\s*day")

_TICKER_RE = re.compile(
    r"(?:trading|trade|traded|listed|listing).{0,160}?symbol\s*"
    r"[“\"]([A-Za-z]{1,6})\.?[”\"]",
    re.IGNORECASE | re.DOTALL,
)
#: Fallback for a cover page that states the ticker with no quotes at all
#: ("under the symbol AVEO."). Deliberately case-SENSITIVE and tried only
#: when the quoted form above does not match: an all-caps word straight
#: after "symbol" is the ticker on every real filing this was checked
#: against, but dropping the quote requirement for every filing would risk
#: catching an unrelated capitalised word ("symbol OF our commitment...").
_TICKER_UNQUOTED_RE = re.compile(
    r"(?:trading|trade|traded|listed|listing).{0,160}?symbol\s+([A-Z]{1,6})\b",
    re.DOTALL,
)

#: Real underwriter lock-ups run 90-180+ days. The clause's own extension
#: machinery ("the last 17 days of the lock-up period", "an 18-day period")
#: uses small numbers in the same section, and without a floor those are
#: indistinguishable from the length itself -- found on the first real
#: filing this was tested against (Textura Corp: a correct 180 alongside a
#: 17 and an 18 from its earnings-blackout extension clause).
_MIN_PLAUSIBLE_LOCKUP_DAYS = 60


@dataclass(frozen=True)
class FilingHit:
    """One filing of the forms searched for, from a UNIQUE company match."""

    cik: str
    conformed_name: str
    form: str
    filed: date
    accession: str
    index_href: str


# Search results that are not a single confirmed filing -- recorded as a
# string status rather than an exception, because "not found" and
# "ambiguous" are expected, common outcomes this pipeline must count, not
# failures that should abort it.
NO_MATCH = "no_filing_found"
AMBIGUOUS_NAME = "multiple_name_matches"
UNSEARCHABLE_NAME = "name_not_searchable"
FETCH_ERROR = "fetch_error"


def search_prefix(name: str) -> str | None:
    """The word EDGAR's company-name search is queried with.

    EDGAR's ``company=`` parameter matches from the START of the
    registrant's name, so the stored name (which may carry a suffix EDGAR
    spells differently -- "Corp" vs "Corporation" -- or omits) is truncated
    to its first distinctive word. A candidate whose first word is only a
    generic opener ("American", "The", "National", ...) returns far too
    many unrelated registrants to disambiguate automatically, so it is
    reported unsearchable rather than guessed at.
    """
    words = _SEARCH_WORD_RE.findall(name or "")
    for word in words:
        if len(word) > 1 and word.lower() not in _GENERIC_FIRST_WORDS:
            return word
    return None


def parse_company_search_atom(
    xml_text: str, form: str
) -> list[FilingHit] | str:
    """Filings from a ``browse-edgar`` atom response, or why there are none.

    EDGAR returns two different shapes depending on how many registrants
    matched the name:

    - A UNIQUE match puts one ``<company-info>`` directly under ``<feed>``,
      followed by one ``<entry>`` per FILING (accession, filing-date, ...).
      This is the shape this function extracts.
    - An AMBIGUOUS match (more than one registrant) puts a
      ``<company-info>`` inside each entry's ``<content>`` instead, with no
      filing details -- a company list, not a filing list. Detected and
      reported as ``AMBIGUOUS_NAME`` rather than parsed, because picking
      one of several same-prefix companies without reading anything is a
      guess, not an identification.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return FETCH_ERROR

    company_info = root.find(f"{_ATOM_NS}company-info")
    entries = root.findall(f"{_ATOM_NS}entry")
    if company_info is None:
        if any(e.find(f"{_ATOM_NS}content/{_ATOM_NS}company-info") is not None for e in entries):
            return AMBIGUOUS_NAME
        return NO_MATCH

    cik_el = company_info.find(f"{_ATOM_NS}cik")
    name_el = company_info.find(f"{_ATOM_NS}conformed-name")
    cik = (cik_el.text or "").strip() if cik_el is not None else ""
    name = (name_el.text or "").strip() if name_el is not None else ""
    if not cik:
        return NO_MATCH

    hits: list[FilingHit] = []
    for entry in entries:
        content = entry.find(f"{_ATOM_NS}content")
        link = entry.find(f"{_ATOM_NS}link")
        if content is None:
            continue
        filed_el = content.find(f"{_ATOM_NS}filing-date")
        acc_el = content.find(f"{_ATOM_NS}accession-number")
        if filed_el is None or filed_el.text is None or acc_el is None or acc_el.text is None:
            continue
        try:
            filed = date.fromisoformat(filed_el.text.strip())
        except ValueError:
            continue
        hits.append(FilingHit(
            cik=cik, conformed_name=name, form=form, filed=filed,
            accession=acc_el.text.strip(),
            index_href=link.get("href", "") if link is not None else "",
        ))
    if not hits:
        return NO_MATCH
    return hits


def extract_cover_ticker(text: str, window: int = 6000) -> str | None:
    """The ticker a prospectus's own cover page states.

    Read from the document itself rather than assumed from our database --
    a second, unrelated company sharing a name prefix would otherwise
    silently pass as a match. Only the first ``window`` characters (the
    cover page) are searched, so a ticker mentioned incidentally deep in
    "Underwriting" is not picked up as if it were the issuer's own.

    The gap the regex allows between a trigger word and "symbol" was
    widened from 80 to 160 characters after a real false negative: Terreno
    Realty's cover page (2010-02-10 424B1) reads "approved for listing on
    the New York Stock Exchange, or NYSE, subject to official notice of
    issuance, under the symbol..." -- 92 characters of ordinary exchange
    boilerplate between "listing" and "symbol" that the narrower gap
    rejected outright, reporting a confirmable IPO as a ticker mismatch.

    The unquoted fallback exists because not every cover page quotes the
    ticker at all: AVEO Pharmaceuticals' (2010-03-12 424B4) reads "under
    the symbol AVEO." with no quotation marks of any kind.

    The gap between the trigger word and "symbol" allows ANY character,
    periods included -- MaxLinear's cover page (2010-03-24 424B4) reads
    "...on the New York Stock Exchange, Inc. under the symbol..." and an
    earlier version of this regex excluded periods from the gap entirely,
    which "Inc." broke on the second real filing this was checked against.
    """
    head = text[:window]
    match = _TICKER_RE.search(head)
    if match is None:
        match = _TICKER_UNQUOTED_RE.search(head)
    return match.group(1).upper() if match else None


def extract_lockup_days(text: str, window: int = 3000) -> tuple[int | None, str]:
    """The lock-up length in days, read from the clause itself.

    Anchors on the LAST occurrence of "lock-up agreement(s)" in the
    document -- prospectuses typically name it once early as a
    cross-reference and again, substantively, inside "Underwriting" -- and
    reads forward from there. A candidate day-count is discarded if "Rule
    144" appears within 60 characters of it: Rule 144's own resale-
    eligibility clock is frequently phrased with the identical anchor
    ("... days after the date of this prospectus"), and conflating the two
    was found on the first real filing this was tested against (Textura
    Corp, 2013-06-06 424B4: Rule 144 at 90 days sits close enough to the
    lock-up's own 180 to be read as the same clause by a naive scan). A
    candidate below ``_MIN_PLAUSIBLE_LOCKUP_DAYS`` is also discarded: the
    same clause's own earnings-blackout extension language ("the last 17
    days of the lock-up period", "an 18-day period") introduces small
    numbers that are not the lock-up's length, found on the same filing.

    Returns ``(days, status)``. ``status`` is ``"ok"``,
    ``"no_lockup_section"`` (the heading itself was not found),
    ``"no_day_count"`` (found the section, no digit-day pattern in it), or
    ``"ambiguous"`` (more than one distinct day count survived the Rule 144
    filter -- not guessed at, excluded).
    """
    matches = list(_LOCKUP_SECTION_RE.finditer(text))
    if not matches:
        return None, "no_lockup_section"
    start = matches[-1].start()
    section = text[start:start + window]

    candidates: list[int] = []
    for m in _DAY_RE.finditer(section):
        value = int(m.group(1))
        if value < _MIN_PLAUSIBLE_LOCKUP_DAYS:
            continue
        context = section[max(0, m.start() - 60): m.end() + 60]
        if _RULE144_RE.search(context):
            continue
        candidates.append(value)

    distinct = sorted(set(candidates))
    if not distinct:
        return None, "no_day_count"
    if len(distinct) > 1:
        return None, "ambiguous"
    return distinct[0], "ok"


def parse_fts_hits(payload: dict, ticker: str) -> list[FilingHit] | str:
    """Full text search hits for one ticker -> ``FilingHit`` list, or why
    there is not a confirmed one.

    Each hit's ``_id`` is ``"<accession>:<primary-document-filename>"`` --
    full text search hands over the document's own filename directly, so
    (unlike the name-search path) no second request to read a filing's
    ``index.json`` is needed to find it. The filename is stashed in
    ``FilingHit.index_href`` for ``build_lockup_table`` to split back out.

    More than one DISTINCT company (by CIK) among the hits is reported as
    ``AMBIGUOUS_NAME``: the ticker matched more than one registrant's
    filing in the window, and picking one without reading anything is a
    guess, not an identification.
    """
    hits = ((payload or {}).get("hits") or {}).get("hits") or []
    if not hits:
        return NO_MATCH

    ciks = {tuple(h.get("_source", {}).get("ciks") or []) for h in hits}
    if len(ciks) > 1:
        return AMBIGUOUS_NAME

    out: list[FilingHit] = []
    for h in hits:
        source = h.get("_source") or {}
        cik_list = source.get("ciks") or []
        hit_id = str(h.get("_id") or "")
        if not cik_list or ":" not in hit_id:
            continue
        try:
            filed = date.fromisoformat(str(source.get("file_date")))
        except (TypeError, ValueError):
            continue
        accession = hit_id.split(":", 1)[0]
        names = source.get("display_names") or [""]
        out.append(FilingHit(
            cik=cik_list[0], conformed_name=str(names[0]),
            form=str(source.get("form") or ""), filed=filed,
            accession=accession, index_href=hit_id,
        ))
    return out if out else NO_MATCH


class EdgarCompanySearch:
    """Looks a company up by name in EDGAR's full historical registrant
    index, and fetches plain documents. Separate from ``EdgarProvider``
    (which reads the current ticker map and the structured XBRL/submissions
    APIs) because this reads a different endpoint family -- see the module
    docstring for why the current ticker map cannot do this job.
    """

    name = "edgar_company_search"

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self.settings = settings or get_settings()
        agent = (self.settings.sec_user_agent or "").strip()
        if not agent or "@" not in agent:
            raise ProviderError(
                "SEC_USER_AGENT must be set to a descriptive string containing a "
                "contact email; see providers/edgar.py."
            )
        self._client = client or httpx.Client(
            timeout=self.settings.request_timeout_seconds,
            headers={"User-Agent": agent},
            follow_redirects=True,
        )
        self._last_request = 0.0

    def _get(self, url: str, params: dict | None = None, *, retries: int = 3) -> httpx.Response:
        """One rate-limited GET, retrying a transient 5xx with backoff.

        `efts.sec.gov` (full text search) returned intermittent 500s during
        this module's own construction run -- not tied to any particular
        query, and gone on an immediate retry -- unlike the data.sec.gov
        endpoints `EdgarProvider` calls, which this project has not seen do
        that. A 4xx (a malformed query, a missing resource) is not retried:
        trying the same request again would not change a client error.
        """
        last_exc: httpx.HTTPError | None = None
        for attempt in range(retries):
            elapsed = time.monotonic() - self._last_request
            if elapsed < REQUEST_INTERVAL:
                time.sleep(REQUEST_INTERVAL - elapsed)
            try:
                response = self._client.get(url, params=params)
                self._last_request = time.monotonic()
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                self._last_request = time.monotonic()
                if exc.response.status_code < 500 or attempt == retries - 1:
                    raise ProviderError(f"EDGAR request failed: {exc}") from exc
                last_exc = exc
                time.sleep(2.0 * (attempt + 1))
            except httpx.HTTPError as exc:
                raise ProviderError(f"EDGAR request failed: {exc}") from exc
        raise ProviderError(f"EDGAR request failed after retries: {last_exc}")

    def _get_text(self, url: str, params: dict | None = None) -> str:
        return self._get(url, params).text

    def _get_json(self, url: str, params: dict | None = None) -> dict:
        try:
            return self._get(url, params).json()
        except ValueError as exc:
            raise ProviderError(f"EDGAR returned unparseable JSON: {exc}") from exc

    def filings_by_ticker(
        self,
        ticker: str,
        around: date,
        *,
        window_days: int = TICKER_SEARCH_WINDOW_DAYS,
        forms: tuple[str, ...] = IPO_PROSPECTUS_FORMS,
    ) -> list[FilingHit] | str:
        """Filings of ``forms`` mentioning ``ticker`` as an exact phrase,
        filed within ``window_days`` of ``around``. The primary
        identification path -- see the module docstring for why this
        replaced a name-based search.
        """
        start = around - timedelta(days=window_days)
        end = around + timedelta(days=window_days)
        payload = self._get_json(FTS_URL, params={
            "q": f'"{ticker}"',
            "forms": ",".join(forms),
            "dateRange": "custom",
            "startdt": start.isoformat(),
            "enddt": end.isoformat(),
        })
        return parse_fts_hits(payload, ticker)

    def filings_by_name(
        self, name_prefix: str, forms: tuple[str, ...] = IPO_PROSPECTUS_FORMS
    ) -> list[FilingHit] | str:
        """Filings of ``forms`` for the company whose name starts with
        ``name_prefix``, trying each form in order and returning the first
        that resolves to a unique company with at least one hit. If every
        form comes back ``NO_MATCH``, that is what is returned; an
        ambiguous or errored lookup on any form is returned immediately
        rather than silently falling through to the next form.
        """
        last = NO_MATCH
        for form in forms:
            xml_text = self._get_text(BROWSE_URL, params={
                "action": "getcompany", "company": name_prefix, "type": form,
                "dateb": "", "owner": "include", "count": "100", "output": "atom",
            })
            result = parse_company_search_atom(xml_text, form)
            if isinstance(result, list):
                return result
            if result != NO_MATCH:
                return result
            last = result
        return last

    def document(self, url: str) -> str:
        return self._get_text(url)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> EdgarCompanySearch:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


def filing_directory_url(cik: str, accession: str) -> str:
    """EDGAR's archive folder for one filing.

    The archive path uses the CIK as a plain integer (no zero-padding,
    unlike the submissions/company-facts APIs) and the accession number
    with its dashes removed.
    """
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}"


def pick_primary_document(index_json_text: str) -> str | None:
    """The filing's own main document -- not an exhibit, not a graphic.

    EDGAR's per-filing ``index.json`` lists every file in the accession's
    folder with no semantic tag for "this one is the prospectus," so this
    picks the largest ``.htm``/``.html`` file that is not the index or
    full-submission-text wrapper. The prospectus itself is reliably the
    largest document in the folder -- hundreds of kilobytes to several
    megabytes -- while exhibits, certifications and graphics are small.
    """
    try:
        payload = json.loads(index_json_text)
    except (ValueError, TypeError):
        return None
    items = ((payload or {}).get("directory") or {}).get("item") or []
    best_name: str | None = None
    best_size = -1
    for item in items:
        name = str(item.get("name") or "")
        lower = name.lower()
        if not (lower.endswith(".htm") or lower.endswith(".html")):
            continue
        if "-index" in lower:
            continue
        try:
            size = int(item.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        if size > best_size:
            best_size, best_name = size, name
    return best_name


_TAG_RE = re.compile(r"<[^>]+>")
_NUMERIC_ENTITY_RE = re.compile(r"&#(\d+);")
_WS_RE = re.compile(r"\s+")


def _decode_legacy_numeric_entity(match: re.Match[str]) -> str:
    """``&#147;`` -> a left curly quote, not the C1 control character its
    number literally names.

    These old EDGAR filings (converted from Word, by the look of them) use
    numeric character references in 128-159 to mean Windows-1252's curly
    quotes, dashes and ellipsis -- the exact substitution browsers make and
    ``html.unescape`` does NOT: it decodes ``&#147;`` to the raw codepoint
    U+0093, a control character, not U+201C. A cover page's own ticker
    quoting ("TRNO") was unreadable by this module's regexes until this
    was found, on the first real filing it was tested against that used
    this style (Terreno Realty, 2010-02-10 424B1) instead of literal
    Unicode quote characters (Textura's, the earlier worked example).
    """
    n = int(match.group(1))
    if 128 <= n <= 159:
        try:
            return bytes([n]).decode("cp1252")
        except UnicodeDecodeError:
            return match.group(0)
    return match.group(0)


def strip_html(raw: str) -> str:
    """Plain text good enough for regex extraction, not for display."""
    text = _TAG_RE.sub(" ", raw)
    text = _NUMERIC_ENTITY_RE.sub(_decode_legacy_numeric_entity, text)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text)


@dataclass(frozen=True)
class LockupRecord:
    """One candidate's outcome: confirmed, or excluded with a stated reason.

    Every candidate this pipeline is given produces exactly one record.
    Nothing is silently dropped -- CHARTER section 7, "every attempt is
    counted."
    """

    ticker: str
    name: str
    first_date: date
    status: str
    cik: str = ""
    accession: str = ""
    filing_date: date | None = None
    filing_href: str = ""
    cover_ticker: str | None = None
    lockup_days: int | None = None
    expiry_date: date | None = None
    detail: str = ""

    @property
    def confirmed(self) -> bool:
        return self.status == "confirmed"


EXCLUDED_NO_DOCUMENT = "no_primary_document"
EXCLUDED_TICKER_MISMATCH = "cover_ticker_mismatch"


def build_lockup_table(
    candidates: list[tuple[str, str, date]],
    search: EdgarCompanySearch,
    *,
    progress=None,
) -> list[LockupRecord]:
    """One ``LockupRecord`` per ``(ticker, name, first_date)`` candidate.

    See the module docstring's construction method. A candidate fails at
    most one step and is recorded with that step's reason; nothing is
    retried with a looser rule. ``name`` is carried through to the output
    for readability only -- identification does not depend on it.
    """
    out: list[LockupRecord] = []
    for i, (ticker, name, first_date) in enumerate(candidates):
        if progress is not None:
            progress(i, len(candidates), ticker)
        ticker_u = ticker.strip().upper()

        try:
            hits = search.filings_by_ticker(ticker_u, first_date)
        except ProviderError as exc:
            out.append(LockupRecord(ticker_u, name, first_date, FETCH_ERROR, detail=str(exc)))
            continue
        if isinstance(hits, str):
            out.append(LockupRecord(ticker_u, name, first_date, hits))
            continue

        # One company, possibly more than one filing in the window (an S-1
        # amendment's own 424B4 alongside the final one). Closest to our
        # own first bar wins; the search already restricted every hit to
        # the same CIK, so this is picking a filing, not a company.
        hit = min(hits, key=lambda h: abs((h.filed - first_date).days))

        directory = filing_directory_url(hit.cik, hit.accession)
        # Full text search hands the primary document's filename over
        # directly (stashed in `index_href` as "<accession>:<filename>");
        # only a hit from the name-search fallback path needs the extra
        # index.json round trip to find it.
        doc_name = hit.index_href.split(":", 1)[1] if ":" in hit.index_href else None
        if doc_name is None:
            try:
                index_json = search.document(f"{directory}/index.json")
            except ProviderError as exc:
                out.append(LockupRecord(
                    ticker_u, name, first_date, FETCH_ERROR, cik=hit.cik,
                    accession=hit.accession, filing_date=hit.filed, detail=str(exc),
                ))
                continue
            doc_name = pick_primary_document(index_json)
        if doc_name is None:
            out.append(LockupRecord(
                ticker_u, name, first_date, EXCLUDED_NO_DOCUMENT,
                cik=hit.cik, accession=hit.accession, filing_date=hit.filed,
            ))
            continue
        doc_url = f"{directory}/{doc_name}"

        try:
            doc_text = strip_html(search.document(doc_url))
        except ProviderError as exc:
            out.append(LockupRecord(
                ticker_u, name, first_date, FETCH_ERROR, cik=hit.cik, accession=hit.accession,
                filing_date=hit.filed, filing_href=doc_url, detail=str(exc),
            ))
            continue

        cover_ticker = extract_cover_ticker(doc_text)
        if cover_ticker != ticker_u:
            out.append(LockupRecord(
                ticker_u, name, first_date, EXCLUDED_TICKER_MISMATCH, cik=hit.cik,
                accession=hit.accession, filing_date=hit.filed, filing_href=doc_url,
                cover_ticker=cover_ticker,
            ))
            continue

        days, status = extract_lockup_days(doc_text)
        if status != "ok":
            out.append(LockupRecord(
                ticker_u, name, first_date, status, cik=hit.cik, accession=hit.accession,
                filing_date=hit.filed, filing_href=doc_url, cover_ticker=cover_ticker,
            ))
            continue

        out.append(LockupRecord(
            ticker_u, name, first_date, "confirmed", cik=hit.cik, accession=hit.accession,
            filing_date=hit.filed, filing_href=doc_url, cover_ticker=cover_ticker,
            lockup_days=days, expiry_date=hit.filed + timedelta(days=days),
        ))
    return out


@dataclass
class LockupBuildSummary:
    records: list[LockupRecord] = field(default_factory=list)

    def by_status(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.records:
            out[r.status] = out.get(r.status, 0) + 1
        return out
