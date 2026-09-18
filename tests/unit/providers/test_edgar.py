"""EDGAR parsing and the earnings-date proxy.

The parsing helpers are pure, so EDGAR's formats are pinned without a network.
Both formats are awkward in the same way -- neither is a list of records -- and
that is exactly where a silent misread would live.
"""

from __future__ import annotations

from datetime import date

import pytest

from screener.config import Settings
from screener.providers.base import ProviderError
from screener.providers.edgar import (
    EdgarProvider,
    earliest_per_period,
    older_submission_pages,
    parse_company_facts,
    parse_submissions,
    parse_ticker_map,
)

TICKER_MAP = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
}

SUBMISSIONS = {
    "filings": {
        "recent": {
            "filingDate": ["2024-02-01", "2024-02-05", "2024-03-11", "2024-05-02"],
            "form":       ["8-K",        "10-Q",       "8-K",        "8-K"],
            "reportDate": ["2023-12-30", "2023-12-30", "",           "2024-03-30"],
            "accessionNumber": ["a1", "a2", "a3", "a4"],
        }
    }
}


def test_ticker_map_is_keyed_by_symbol_and_zero_padded():
    """EDGAR ships positional records in a dict, and CIKs must be padded to ten
    digits or the submissions URL 404s."""
    out = parse_ticker_map(TICKER_MAP)

    assert out["AAPL"] == "0000320193"
    assert len(out["MSFT"]) == 10


def test_ticker_map_survives_a_malformed_record():
    out = parse_ticker_map({"0": {"ticker": "OK", "cik_str": 1}, "1": {"broken": True}})
    assert out == {"OK": "0000000001"}


def test_submissions_are_zipped_back_into_records():
    """The block is stored column-wise -- parallel arrays, not records. Zipping
    them back in the wrong order would misdate every filing."""
    filings = parse_submissions("AAPL", SUBMISSIONS)

    assert len(filings) == 4
    first = filings[0]
    assert first.filed == date(2024, 2, 1)
    assert first.form == "8-K"
    assert first.period == date(2023, 12, 30)


def test_filings_come_back_in_date_order():
    filings = parse_submissions("AAPL", SUBMISSIONS)
    assert [f.filed for f in filings] == sorted(f.filed for f in filings)


def test_a_missing_report_date_is_preserved_at_the_parsing_stage():
    """Parsing keeps everything; deciding what counts as an earnings event is
    a separate step, so the two concerns stay testable apart."""
    filings = parse_submissions("AAPL", SUBMISSIONS)
    undated = [f for f in filings if f.period is None]

    assert len(undated) == 1
    assert undated[0].filed == date(2024, 3, 11)


def test_unrelated_forms_are_ignored():
    payload = {
        "filings": {"recent": {
            "filingDate": ["2024-01-05", "2024-01-06"],
            "form": ["4", "SC 13G"],
            "reportDate": ["", ""],
            "accessionNumber": ["x", "y"],
        }}
    }
    assert parse_submissions("AAPL", payload) == []


def test_empty_payload_yields_nothing_rather_than_raising():
    assert parse_submissions("AAPL", {}) == []
    assert parse_ticker_map({}) == {}


def test_one_event_per_period_preferring_the_press_release():
    """A company files several 8-Ks a quarter for unrelated reasons. Keeping
    every one would multiply a quarterly event into a monthly one."""
    collapsed = earliest_per_period(parse_submissions("AAPL", SUBMISSIONS))

    assert len(collapsed) == 2
    assert collapsed[0].filed == date(2024, 2, 1)
    assert collapsed[0].form == "8-K", "the 8-K precedes the 10-Q for that period"
    assert collapsed[1].filed == date(2024, 5, 2)


def test_the_earliest_filing_wins_within_a_period():
    filings = parse_submissions("X", {
        "filings": {"recent": {
            "filingDate": ["2024-02-20", "2024-02-02"],
            "form": ["10-Q", "8-K"],
            "reportDate": ["2023-12-31", "2023-12-31"],
            "accessionNumber": ["late", "early"],
        }}
    })
    collapsed = earliest_per_period(filings)

    assert len(collapsed) == 1
    assert collapsed[0].accession == "early"


def test_a_user_agent_without_a_contact_is_refused():
    """EDGAR's fair-access policy requires one, and returns 403 without it.
    Failing here beats failing on the ninetieth symbol."""
    with pytest.raises(ProviderError, match="SEC_USER_AGENT"):
        EdgarProvider(Settings(sec_user_agent="screener"))
    with pytest.raises(ProviderError, match="SEC_USER_AGENT"):
        EdgarProvider(Settings(sec_user_agent=""))


def test_a_descriptive_user_agent_is_accepted():
    provider = EdgarProvider(Settings(sec_user_agent="SCREENERV12 me@example.com"))
    assert provider.name == "edgar"
    provider.close()


def test_an_unrelated_8k_does_not_displace_the_earnings_filing():
    """8-Ks are filed for directors resigning, credit agreements, and
    restructurings. Taking merely the earliest filing in a quarter would anchor
    a drift study on whichever unrelated event happened first."""
    filings = parse_submissions("X", {
        "filings": {"recent": {
            "filingDate": ["2024-01-08", "2024-02-02"],
            "form": ["8-K", "8-K"],
            "reportDate": ["", "2023-12-31"],      # first declares no period
            "accessionNumber": ["unrelated", "earnings"],
        }}
    })
    collapsed = earliest_per_period(filings)

    assert [f.accession for f in collapsed] == ["earnings"]


def test_undated_filings_survive_when_a_symbol_has_no_report_dates_at_all():
    """Some registrants supply no reportDate anywhere. For them the undated
    filings are the only signal available, so dropping them loses the symbol
    entirely rather than cleaning it up."""
    filings = parse_submissions("X", {
        "filings": {"recent": {
            "filingDate": ["2024-01-08", "2024-04-09"],
            "form": ["8-K", "8-K"],
            "reportDate": ["", ""],
            "accessionNumber": ["q1", "q2"],
        }}
    })
    assert len(earliest_per_period(filings)) == 2


# --------------------------------------------------------------------------
# XBRL company facts
# --------------------------------------------------------------------------

COMPANY_FACTS = {
    "cik": 320193,
    "facts": {
        "us-gaap": {
            "Assets": {"units": {"USD": [
                {"end": "2023-09-30", "val": 352583000000, "accn": "orig",
                 "form": "10-K", "filed": "2023-11-03", "fy": 2023, "fp": "FY"},
                {"end": "2023-09-30", "val": 352000000000, "accn": "restated",
                 "form": "10-K/A", "filed": "2024-05-01"},
            ]}},
            "StockholdersEquity": {"units": {"USD": [
                {"end": "2023-09-30", "val": 62146000000, "accn": "orig",
                 "form": "10-K", "filed": "2023-11-03"},
            ]}},
            "SomeIrrelevantTag": {"units": {"USD": [
                {"end": "2023-09-30", "val": 1, "accn": "orig",
                 "form": "10-K", "filed": "2023-11-03"},
            ]}},
        },
        "dei": {
            "EntityCommonStockSharesOutstanding": {"units": {"shares": [
                {"end": "2023-09-30", "val": 15550061000, "accn": "orig",
                 "form": "10-K", "filed": "2023-11-03"},
            ]}},
        },
    },
}


def test_company_facts_flatten_to_records():
    facts = parse_company_facts("AAPL", COMPANY_FACTS)
    concepts = {f.concept for f in facts}

    assert "assets" in concepts
    assert "equity" in concepts
    assert "shares_outstanding" in concepts, "dei tags carry the share count"


def test_every_restated_version_is_kept():
    """Discarding old versions makes it impossible to reconstruct what was
    known at a past date, which is the entire reason for storing this."""
    assets = [f for f in parse_company_facts("AAPL", COMPANY_FACTS) if f.concept == "assets"]

    assert len(assets) == 2
    assert {f.accession for f in assets} == {"orig", "restated"}
    assert {f.filed for f in assets} == {date(2023, 11, 3), date(2024, 5, 1)}


def test_unmapped_tags_are_ignored():
    tags = {f.tag for f in parse_company_facts("AAPL", COMPANY_FACTS)}
    assert "SomeIrrelevantTag" not in tags


def test_the_originating_tag_is_preserved():
    """Concepts are many-to-one over tags. Keeping the source tag is what makes
    an odd value auditable rather than mysterious."""
    equity = next(f for f in parse_company_facts("AAPL", COMPANY_FACTS) if f.concept == "equity")
    assert equity.tag == "StockholdersEquity"


def test_units_are_recorded_because_shares_are_not_dollars():
    facts = parse_company_facts("AAPL", COMPANY_FACTS)
    units = {f.concept: f.unit for f in facts}

    assert units["assets"] == "USD"
    assert units["shares_outstanding"] == "shares"


def test_a_record_missing_a_filing_date_is_dropped():
    """Without a filing date there is no way to know when it became public, so
    it cannot be used point-in-time at all."""
    payload = {"facts": {"us-gaap": {"Assets": {"units": {"USD": [
        {"end": "2023-09-30", "val": 100, "accn": "x", "form": "10-K"},
    ]}}}}}
    assert parse_company_facts("AAPL", payload) == []


def test_empty_facts_payload_is_handled():
    assert parse_company_facts("AAPL", {}) == []
    assert parse_company_facts("AAPL", {"facts": {}}) == []


# --------------------------------------------------------------------------
# Older filing pages
#
# `filings.recent` is one page, not the history. Reading only that page fails
# silently -- the early part of a window returns nothing, which looks exactly
# like a company that filed nothing.
# --------------------------------------------------------------------------

PAGED_SUBMISSIONS = {
    "filings": {
        "recent": {
            "filingDate": ["2024-02-01"],
            "form": ["8-K"],
            "reportDate": ["2023-12-30"],
            "accessionNumber": ["recent-1"],
        },
        "files": [
            {"name": "CIK0000320193-submissions-001.json",
             "filingFrom": "2014-01-02", "filingTo": "2019-12-31"},
            {"name": "CIK0000320193-submissions-002.json",
             "filingFrom": "1996-01-02", "filingTo": "2001-12-31"},
        ],
    },
}

OLDER_PAGE = {
    "filingDate": ["2015-04-27", "2015-07-21"],
    "form": ["8-K", "8-K"],
    "reportDate": ["2015-03-28", "2015-06-27"],
    "accessionNumber": ["old-1", "old-2"],
}


def test_an_older_page_parses_with_its_columns_at_the_top_level():
    """The submissions document nests the newest page under filings.recent; an
    older page is a bare document. Same columns, different depth."""
    filings = parse_submissions("AAPL", OLDER_PAGE)

    assert [f.accession for f in filings] == ["old-1", "old-2"]
    assert filings[0].filed == date(2015, 4, 27)


def test_only_pages_overlapping_the_window_are_requested():
    """Every page is a request against a rate-limited API, and a page ending in
    2001 holds nothing for a 2010-2015 study."""
    names = older_submission_pages(
        PAGED_SUBMISSIONS, date(2010, 1, 1), date(2015, 12, 31)
    )

    assert names == ["CIK0000320193-submissions-001.json"]


def test_a_page_whose_range_will_not_parse_is_fetched_anyway():
    """Missing filings is the failure that cost a run. An unreadable range is
    a reason to look, not a reason to skip."""
    payload = {"filings": {"files": [
        {"name": "unparseable.json", "filingFrom": "", "filingTo": "nonsense"},
    ]}}

    assert older_submission_pages(payload, date(2010, 1, 1), date(2015, 1, 1)) == [
        "unparseable.json"
    ]


def test_no_files_block_asks_for_nothing():
    assert older_submission_pages(SUBMISSIONS, date(2010, 1, 1), date(2020, 1, 1)) == []
    assert older_submission_pages({}, date(2010, 1, 1), date(2020, 1, 1)) == []


def _paged_provider():
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "company_tickers" in url:
            return httpx.Response(200, json=TICKER_MAP)
        if url.endswith("CIK0000320193.json"):
            return httpx.Response(200, json=PAGED_SUBMISSIONS)
        if url.endswith("CIK0000320193-submissions-001.json"):
            return httpx.Response(200, json=OLDER_PAGE)
        return httpx.Response(404, json={})

    return EdgarProvider(
        Settings(sec_user_agent="SCREENERV12 me@example.com"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_history_older_than_the_recent_page_is_actually_returned():
    """The regression this exists for: 10,391 events ingested but only 1,218
    inside the 2010-2015 split, because everything older than the recent page
    was never requested."""
    with _paged_provider() as provider:
        filings = provider.get_filings("AAPL", date(2010, 1, 1), date(2015, 12, 31))

    assert [f.accession for f in filings] == ["old-1", "old-2"]


def test_a_filing_on_two_pages_is_counted_once():
    """Pages are not documented as disjoint, and the same filing twice would
    read as two separate announcements."""
    import httpx

    overlapping = dict(OLDER_PAGE)
    overlapping["accessionNumber"] = ["recent-1", "old-2"]
    overlapping["filingDate"] = ["2024-02-01", "2015-07-21"]

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "company_tickers" in url:
            return httpx.Response(200, json=TICKER_MAP)
        if url.endswith("CIK0000320193.json"):
            return httpx.Response(200, json=PAGED_SUBMISSIONS)
        return httpx.Response(200, json=overlapping)

    provider = EdgarProvider(
        Settings(sec_user_agent="SCREENERV12 me@example.com"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with provider:
        filings = provider.get_filings("AAPL", date(2010, 1, 1), date(2024, 12, 31))

    assert [f.accession for f in filings] == ["old-2", "recent-1"]
