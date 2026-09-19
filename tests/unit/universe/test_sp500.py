"""Point-in-time S&P 500 membership.

The universe decision of 2026-09-19 rests on this file being read correctly:
membership as of a date, including the companies that later failed or were
bought, which a universe of today's large caps cannot contain.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from screener.db.models import Symbol, UniverseSnapshot
from screener.universe.build import universe_members
from screener.universe.sp500 import load, parse
from tests.unit.ingest.conftest import session  # noqa: F401

CSV = '''date,tickers
2010-01-04,"AAPL,MSFT,AAMRQ-201312"
2013-06-03,"AAPL,MSFT,FB"
'''


def components(tmp_path, text: str = CSV):
    path = tmp_path / "components.csv"
    path.write_text(text, encoding="utf-8")
    return parse(path)


def test_membership_is_read_as_of_the_dates_it_changed(tmp_path):
    snapshots = components(tmp_path)

    assert [s.date for s in snapshots] == [date(2010, 1, 4), date(2013, 6, 3)]
    assert "FB" in snapshots[1].tickers
    assert "FB" not in snapshots[0].tickers


def test_a_delisting_suffix_is_stripped_and_the_company_kept(tmp_path):
    """`AAMRQ-201312` is AMR Corp, which went bankrupt in 2013. A universe
    that drops it has the survivorship bias this file exists to remove."""
    snapshots = components(tmp_path)

    assert "AAMRQ" in snapshots[0].tickers
    assert not any("-" in t for s in snapshots for t in s.tickers)


def test_loading_creates_symbols_for_companies_with_no_price_data(tmp_path, session):  # noqa: F811
    """Recording that a company WAS in the universe is the point. Whether bars
    exist for it is a separate gap, and one that can then be counted."""
    result = load(session, components(tmp_path), version="test@2026-09-19")
    session.flush()

    assert result.symbols_created == 4        # AAPL, MSFT, AAMRQ, FB
    assert result.rows == 6                   # three names on each of two dates
    tickers = {s.ticker for s in session.scalars(select(Symbol))}
    assert "AAMRQ" in tickers


def test_membership_resolves_as_of_a_date_between_changes(tmp_path, session):  # noqa: F811
    """The file records only the days membership changed, so an exact-date
    lookup would report an empty universe on every other day."""
    load(session, components(tmp_path), name="sp500_pit", version="test")
    session.flush()

    assert universe_members(session, "sp500_pit", date(2011, 7, 1)) == [
        "AAMRQ", "AAPL", "MSFT",
    ]
    assert "FB" in universe_members(session, "sp500_pit", date(2014, 1, 2))


def test_a_date_before_the_first_snapshot_has_no_universe(tmp_path, session):  # noqa: F811
    """Never resolve forward: the universe was not defined yet."""
    load(session, components(tmp_path), name="sp500_pit", version="test")
    session.flush()

    assert universe_members(session, "sp500_pit", date(2009, 1, 2)) == []


def test_reloading_restates_rather_than_layering(tmp_path, session):  # noqa: F811
    """This source is corrected by hand every few months. A reload must
    replace the membership, not leave two versions of it in the table."""
    snapshots = components(tmp_path)
    load(session, snapshots, name="sp500_pit", version="v1")
    load(session, snapshots, name="sp500_pit", version="v2")
    session.flush()

    rows = session.scalars(
        select(UniverseSnapshot).where(UniverseSnapshot.name == "sp500_pit")
    ).all()
    assert len(rows) == 6, "the first load's rows were replaced, not added to"
    assert {r.definition_version for r in rows} == {"v2"}


def test_a_window_limits_what_is_loaded(tmp_path, session):  # noqa: F811
    result = load(
        session, components(tmp_path), name="sp500_pit", version="test",
        start=date(2011, 1, 1),
    )
    assert result.snapshots == 1
    assert result.first == date(2013, 6, 3)
