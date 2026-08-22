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
