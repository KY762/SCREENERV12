"""Ticker identity: is this series the company we think it is?

Measured on the database 2026-09-19: BBBY's 2013-2015 prices are Overstock's,
BBT runs unbroken through a 2019 merger that retired the ticker, and EMC's
series starts in 2023, seven years after Dell bought EMC Corp.
"""

from __future__ import annotations

from datetime import date

from screener.diagnostics.stale_series import (
    Identity,
    Series,
    identity_conflicts,
    identity_risks,
)

ENDS = date(2026, 9, 18)


def series(symbol, first, last, bars=4000):
    return Series(symbol=symbol, first_bar=first, last_bar=last, bars=bars)


def test_a_series_starting_after_the_company_left_is_absent_history():
    """EMC Corp was bought by Dell in 2016 and our EMC series starts in 2023.
    The old company's history is missing, so a 2010-2015 backtest finds
    nothing -- a gap, which can at least be counted."""
    risks = identity_risks(
        [series("EMC", date(2023, 5, 15), ENDS)],
        {"EMC": date(2016, 9, 6)},
        data_ends=ENDS,
    )

    assert [r.mode for r in risks] == ["absent"]
    assert "history is missing" in risks[0].detail


def test_a_continuous_series_spanning_a_dead_membership_is_overwritten():
    """BBBY: unbroken 2009-2026, and the middle of it is Overstock. Nothing
    about the series looks wrong, which is what makes it dangerous."""
    risks = identity_risks(
        [series("BBBY", date(2009, 1, 2), date(2026, 9, 4))],
        {"BBBY": date(2017, 7, 25)},
        data_ends=ENDS,
    )

    assert [r.mode for r in risks] == ["overwritten"]
    assert "possibly two companies" in risks[0].detail


def test_a_ticker_that_stopped_trading_is_not_a_risk():
    """SIVB ends the week the bank failed. That is the data being right."""
    assert identity_risks(
        [series("SIVB", date(2009, 1, 2), date(2023, 3, 9))],
        {"SIVB": date(2023, 3, 15)},
        data_ends=ENDS,
    ) == []


def test_a_company_still_in_the_universe_is_not_reported():
    """Only tickers that LEFT are candidates; a current member is just a
    current member."""
    assert identity_risks(
        [series("AAPL", date(2009, 1, 2), ENDS)], {}, data_ends=ENDS
    ) == []


def test_an_innocent_survivor_is_still_reported_as_evidence_not_verdict():
    """AAP left the index and trades on as itself. The check cannot know that
    -- distinguishing it from a reused ticker needs to know whether the
    original company still exists, which is not in the price data. So it is
    reported, labelled, and left to a person."""
    risks = identity_risks(
        [series("AAP", date(2009, 1, 2), ENDS)],
        {"AAP": date(2023, 7, 10)},
        data_ends=ENDS,
    )

    assert [r.mode for r in risks] == ["overwritten"]
    assert "possibly" in risks[0].detail, "phrased as a candidate, not a finding"


# --------------------------------------------------------------------------
# Identity conflicts: where the recorded identity contradicts the prices
# --------------------------------------------------------------------------

def ident(symbol, name, kind="Common Stock", active=True, isin="US0000000000"):
    return Identity(symbol=symbol, name=name, security_type=kind,
                    is_active=active, isin=isin)


def test_an_index_member_whose_ticker_is_now_an_etf():
    """FB. Facebook was a member 2013-2022, renamed to META, and the letters
    now belong to a ProShares buffer ETF. An index member is a company, so the
    series downloaded under FB is not that company."""
    conflicts = identity_conflicts(
        [series("FB", date(2025, 6, 26), ENDS)],
        {"FB": ident("FB", "ProShares S&P 500 Dynamic Buffer ETF", kind="ETF")},
        {"FB": date(2022, 6, 8)},
        data_ends=ENDS,
    )

    assert [c.kind for c in conflicts] == ["not_a_stock"]
    assert "ETF" in conflicts[0].detail
    assert conflicts[0].holder.startswith("ProShares")


def test_a_security_the_vendor_calls_delisted_that_keeps_printing_prices():
    """BBBY: listed as Bed Bath & Beyond and delisted, yet priced into 2026
    with Overstock's numbers. The vendor's own list contradicts its prices."""
    conflicts = identity_conflicts(
        [series("BBBY", date(2009, 1, 2), date(2026, 9, 4))],
        {"BBBY": ident("BBBY", "Bed Bath & Beyond, Inc.", active=False)},
        {"BBBY": date(2017, 7, 25)},
        data_ends=ENDS,
    )

    assert [c.kind for c in conflicts] == ["outlived_its_security"]
    assert "disagree" in conflicts[0].detail


def test_a_correctly_delisted_security_is_not_a_conflict():
    """SIVB is delisted and its prices stop the week the bank failed. The list
    and the prices agree, which is the data being right."""
    assert identity_conflicts(
        [series("SIVB", date(2009, 1, 2), date(2023, 3, 9))],
        {"SIVB": ident("SIVB", "SVB Financial Group", active=False)},
        {"SIVB": date(2023, 3, 15)},
        data_ends=ENDS,
    ) == []


def test_a_live_member_that_simply_left_the_index_is_not_a_conflict():
    """AAP shrank out of the index and trades on as itself: common stock,
    listed, with history covering its membership."""
    assert identity_conflicts(
        [series("AAP", date(2009, 1, 2), ENDS)],
        {"AAP": ident("AAP", "Advance Auto Parts Inc")},
        {"AAP": date(2023, 7, 10)},
        data_ends=ENDS,
    ) == []


def test_missing_earlier_history_is_still_reported():
    conflicts = identity_conflicts(
        [series("EMCX", date(2023, 5, 15), ENDS)],
        {"EMCX": ident("EMCX", "Something Else Inc")},
        {"EMCX": date(2016, 9, 6)},
        data_ends=ENDS,
    )
    assert [c.kind for c in conflicts] == ["absent"]


def test_a_reused_ticker_of_the_same_type_is_not_caught_and_that_is_stated():
    """BBT now reads 'Beacon Financial Corporation', not BB&T. Listed, common
    stock, continuous history -- no rule here can catch it, which is why the
    holder's name is reported for a person to read."""
    conflicts = identity_conflicts(
        [series("BBT", date(2009, 1, 2), ENDS)],
        {"BBT": ident("BBT", "Beacon Financial Corporation")},
        {"BBT": date(2019, 12, 5)},
        data_ends=ENDS,
    )

    assert conflicts == [], "no signal fires -- the name is the only clue"
