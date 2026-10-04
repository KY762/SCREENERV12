"""Lock-up extraction: what would break if the parsing silently drifted.

``TEXTURA_EXCERPT`` below is the real text (abbreviated) of Textura Corp's
2013-06-06 424B4 lock-up and Rule 144 passages -- the filing this module's
own docstring cites as the worked example and the Rule 144 confusability
trap. If these tests pass against a hand-trimmed excerpt but the real
filing (fetched live) gives a different answer, the excerpt has drifted
from reality, not the other way around.
"""

from __future__ import annotations

from datetime import date, timedelta

from screener.ingest.lockups import (
    AMBIGUOUS_NAME,
    EXCLUDED_TICKER_MISMATCH,
    NO_MATCH,
    FilingHit,
    build_lockup_table,
    extract_cover_ticker,
    extract_lockup_days,
    filing_directory_url,
    parse_company_search_atom,
    parse_fts_hits,
    pick_primary_document,
    search_prefix,
    strip_html,
)

TEXTURA_EXCERPT = """
Any shares purchased by these investors will be subject to lock-up
restrictions described in "Underwriting."
...
Rule 144

In general, under Rule 144, beginning 90 days after the date of this
prospectus, a person who is not our affiliate and has not been our
affiliate at any time during the preceding three months will be entitled
to sell shares of our common stock.
...
Lock-Up Agreements

We, our officers and directors, and the holders of substantially all of
our common stock have agreed, subject to certain exceptions, not to
directly or indirectly offer, sell, contract to sell, pledge or otherwise
dispose of any shares of common stock without the prior written consent of
Credit Suisse Securities (USA) LLC for a period of 180 days after the date
of this prospectus. However, in the event that we cease to be an emerging
growth company during the "lock-up" period and we release earnings results
during the last 17 days of the "lock-up" period, the expiration of the
"lock-up" will be extended until the expiration of an 18-day period.
"""

TEXTURA_COVER = """
Shares of our common stock have been approved for listing on the New York
Stock Exchange under the symbol "TXTR."
"""


def test_extract_lockup_days_reads_the_clause_not_the_rule_144_proxy():
    days, status = extract_lockup_days(TEXTURA_EXCERPT)
    assert (days, status) == (180, "ok")


def test_extract_lockup_days_missing_section_is_reported_not_guessed():
    days, status = extract_lockup_days("No lock-up language anywhere here.")
    assert (days, status) == (None, "no_lockup_section")


def test_extract_lockup_days_two_distinct_counts_is_ambiguous():
    text = (
        "Lock-Up Agreement: the restricted period is 90 days after closing. "
        "A separate undertaking runs for 180 days after the same date."
    )
    days, status = extract_lockup_days(text)
    assert (days, status) == (None, "ambiguous")


def test_extract_cover_ticker_reads_the_quoted_symbol():
    assert extract_cover_ticker(TEXTURA_COVER) == "TXTR"


def test_extract_cover_ticker_absent_is_none():
    assert extract_cover_ticker("Nothing about a ticker here.") is None


def test_extract_cover_ticker_handles_an_unquoted_cover_page():
    """AVEO Pharmaceuticals' 2010-03-12 424B4: no quotation marks at all."""
    text = (
        "Our common stock has been approved for listing on the NASDAQ "
        "Global Market under the symbol AVEO."
    )
    assert extract_cover_ticker(text) == "AVEO"


def test_extract_cover_ticker_unquoted_fallback_requires_uppercase():
    text = "approved for listing on the exchange under the symbol of our firm."
    assert extract_cover_ticker(text) is None


def test_extract_cover_ticker_gap_may_contain_a_period():
    """MaxLinear's 2010-03-24 424B4: "New York Stock Exchange, Inc. under
    the symbol" -- "Inc." puts a period between the trigger word and
    "symbol"."""
    text = (
        "approved for listing on the New York Stock Exchange, Inc. under "
        "the symbol “MXL.”"
    )
    assert extract_cover_ticker(text) == "MXL"


def test_search_prefix_skips_generic_openers():
    assert search_prefix("American Biotech Corp") == "Biotech"
    assert search_prefix("Textura Corporation") == "Textura"
    assert search_prefix("The") is None


UNIQUE_ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <company-info>
    <cik>0001565337</cik>
    <conformed-name>Textura Corp</conformed-name>
  </company-info>
  <entry>
    <content>
      <accession-number>0001047469-13-006835</accession-number>
      <filing-date>2013-06-06</filing-date>
    </content>
    <link href="https://example.test/filing-index.htm" rel="alternate" type="text/html"/>
  </entry>
</feed>
"""

AMBIGUOUS_ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <content>
      <company-info>
        <cik>0000000001</cik>
      </company-info>
    </content>
  </entry>
  <entry>
    <content>
      <company-info>
        <cik>0000000002</cik>
      </company-info>
    </content>
  </entry>
</feed>
"""

EMPTY_ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"></feed>
"""


def test_parse_company_search_atom_unique_match_returns_filing_hits():
    hits = parse_company_search_atom(UNIQUE_ATOM, "424B4")
    assert not isinstance(hits, str)
    assert len(hits) == 1
    hit = hits[0]
    assert hit.cik == "0001565337"
    assert hit.conformed_name == "Textura Corp"
    assert hit.filed == date(2013, 6, 6)
    assert hit.accession == "0001047469-13-006835"


def test_parse_company_search_atom_multi_company_list_is_ambiguous():
    assert parse_company_search_atom(AMBIGUOUS_ATOM, "424B4") == AMBIGUOUS_NAME


def test_parse_company_search_atom_no_hits_is_no_match():
    assert parse_company_search_atom(EMPTY_ATOM, "424B4") == NO_MATCH


def test_strip_html_removes_tags_and_collapses_whitespace():
    assert strip_html("<p>Hello&nbsp;<b>world</b></p>\n\n  there").strip() == "Hello world there"


def test_strip_html_decodes_legacy_windows_1252_numeric_quotes():
    """Terreno Realty's 2010-02-10 424B1 (the real filing this regression
    is pinned to) quotes its own ticker with &#147;/&#148;, not literal
    curly-quote characters."""
    decoded = strip_html(
        "approved for listing on the New York Stock Exchange under the "
        "symbol &#147;TRNO&#148;."
    )
    assert extract_cover_ticker(decoded) == "TRNO"


def test_filing_directory_url_drops_cik_padding_and_accession_dashes():
    url = filing_directory_url("0001565337", "0001047469-13-006835")
    assert url == "https://www.sec.gov/Archives/edgar/data/1565337/000104746913006835"


INDEX_JSON = """
{"directory": {"item": [
    {"name": "0001047469-13-006835-index.htm", "size": "9000"},
    {"name": "a2215588z424b4.htm", "size": "2498762"},
    {"name": "g354594.jpg", "size": "16748"}
]}}
"""


def test_pick_primary_document_is_the_largest_non_index_htm():
    assert pick_primary_document(INDEX_JSON) == "a2215588z424b4.htm"


def test_pick_primary_document_malformed_json_returns_none():
    assert pick_primary_document("not json") is None


FTS_PAYLOAD_ONE_HIT = {
    "hits": {"hits": [{
        "_id": "0001047469-10-000546:a2196296z424b4.htm",
        "_source": {
            "ciks": ["0001446847"],
            "file_date": "2010-02-04",
            "form": "424B4",
            "display_names": ["IRONWOOD PHARMACEUTICALS INC  (IRWD)  (CIK 0001446847)"],
        },
    }]}
}

FTS_PAYLOAD_TWO_COMPANIES = {
    "hits": {"hits": [
        {"_id": "a:x.htm", "_source": {"ciks": ["1"], "file_date": "2010-02-04"}},
        {"_id": "b:y.htm", "_source": {"ciks": ["2"], "file_date": "2010-02-05"}},
    ]}
}

FTS_PAYLOAD_EMPTY = {"hits": {"hits": []}}


def test_parse_fts_hits_single_hit_resolves():
    hits = parse_fts_hits(FTS_PAYLOAD_ONE_HIT, "IRWD")
    assert not isinstance(hits, str)
    assert len(hits) == 1
    hit = hits[0]
    assert hit.cik == "0001446847"
    assert hit.accession == "0001047469-10-000546"
    assert hit.filed == date(2010, 2, 4)
    assert hit.index_href == "0001047469-10-000546:a2196296z424b4.htm"


def test_parse_fts_hits_two_distinct_companies_is_ambiguous():
    assert parse_fts_hits(FTS_PAYLOAD_TWO_COMPANIES, "AB") == AMBIGUOUS_NAME


def test_parse_fts_hits_no_hits_is_no_match():
    assert parse_fts_hits(FTS_PAYLOAD_EMPTY, "ZZZZ") == NO_MATCH


class FakeSearch:
    """Stands in for ``EdgarCompanySearch`` with canned, offline responses."""

    def __init__(
        self,
        filings_by_ticker: dict[str, list[FilingHit] | str],
        documents: dict[str, str],
    ):
        self._filings = filings_by_ticker
        self._documents = documents

    def filings_by_ticker(self, ticker, around):
        return self._filings.get(ticker, NO_MATCH)

    def document(self, url):
        return self._documents[url]


def _hit(
    cik="0001565337", filed=date(2013, 6, 6), accession="0001047469-13-006835",
    doc="a2215588z424b4.htm",
):
    """An FTS-shaped hit: the document name travels in ``index_href`` as
    ``"<accession>:<filename>"``, exactly as ``parse_fts_hits`` stashes it."""
    return FilingHit(
        cik=cik, conformed_name="Textura Corp", form="424B4",
        filed=filed, accession=accession, index_href=f"{accession}:{doc}",
    )


def test_build_lockup_table_confirms_a_clean_match():
    directory = filing_directory_url("0001565337", "0001047469-13-006835")
    search = FakeSearch(
        filings_by_ticker={"TXTR": [_hit()]},
        documents={
            f"{directory}/a2215588z424b4.htm": (
                '<html>' + TEXTURA_COVER + TEXTURA_EXCERPT + '</html>'
            ),
        },
    )
    records = build_lockup_table([("TXTR", "Textura Corporation", date(2013, 6, 10))], search)
    assert len(records) == 1
    r = records[0]
    assert r.confirmed
    assert r.lockup_days == 180
    assert r.cover_ticker == "TXTR"
    assert r.expiry_date == date(2013, 6, 6) + timedelta(days=180)


def test_build_lockup_table_falls_back_to_index_json_without_an_embedded_name():
    """A hit with no colon in ``index_href`` (the name-search path's shape)
    still resolves, via the extra index.json round trip."""
    directory = filing_directory_url("0001565337", "0001047469-13-006835")
    bare_hit = FilingHit(
        cik="0001565337", conformed_name="Textura Corp", form="424B4",
        filed=date(2013, 6, 6), accession="0001047469-13-006835", index_href="no-colon-here",
    )
    search = FakeSearch(
        filings_by_ticker={"TXTR": [bare_hit]},
        documents={
            f"{directory}/index.json": INDEX_JSON,
            f"{directory}/a2215588z424b4.htm": (
                '<html>' + TEXTURA_COVER + TEXTURA_EXCERPT + '</html>'
            ),
        },
    )
    records = build_lockup_table([("TXTR", "Textura Corporation", date(2013, 6, 10))], search)
    assert records[0].confirmed


def test_build_lockup_table_picks_the_nearest_filing_when_more_than_one():
    near = _hit(filed=date(2013, 6, 6))
    far = _hit(filed=date(2013, 6, 20), accession="0001047469-13-999999", doc="other.htm")
    directory = filing_directory_url("0001565337", "0001047469-13-006835")
    search = FakeSearch(
        filings_by_ticker={"TXTR": [far, near]},
        documents={
            f"{directory}/a2215588z424b4.htm": (
                '<html>' + TEXTURA_COVER + TEXTURA_EXCERPT + '</html>'
            ),
        },
    )
    records = build_lockup_table([("TXTR", "Textura Corporation", date(2013, 6, 10))], search)
    assert records[0].confirmed
    assert records[0].filing_date == date(2013, 6, 6)


def test_build_lockup_table_rejects_a_cover_ticker_mismatch():
    directory = filing_directory_url("0001565337", "0001047469-13-006835")
    search = FakeSearch(
        filings_by_ticker={"TXTR": [_hit()]},
        documents={
            f"{directory}/a2215588z424b4.htm": (
                '<html>Shares trade under the symbol "ABCD."' + TEXTURA_EXCERPT + '</html>'
            ),
        },
    )
    records = build_lockup_table([("TXTR", "Textura Corporation", date(2013, 6, 10))], search)
    assert records[0].status == EXCLUDED_TICKER_MISMATCH
    assert records[0].cover_ticker == "ABCD"


def test_build_lockup_table_counts_every_candidate_exactly_once():
    search = FakeSearch(filings_by_ticker={}, documents={})
    records = build_lockup_table(
        [
            ("TXTR", "Textura Corporation", date(2013, 6, 10)),
            ("ZZZZ", "Unrelated", date(2013, 1, 1)),
        ],
        search,
    )
    assert len(records) == 2
    assert all(r.status == NO_MATCH for r in records)
