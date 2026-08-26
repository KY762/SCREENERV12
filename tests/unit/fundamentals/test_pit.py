"""Point-in-time retrieval.

This is the single place where fundamental look-ahead can enter the platform,
so the tests are written as attacks: each one describes a way to accidentally
see the future and asserts it does not happen.
"""

from __future__ import annotations

from datetime import date

from screener.db.models import Fundamental, Symbol
from screener.fundamentals.pit import fact_as_of, facts_as_of, history
from tests.unit.ingest.conftest import session  # noqa: F401


def add_symbol(session, ticker="AAA"):  # noqa: F811
    symbol = Symbol(ticker=ticker, name=ticker, asset_type="equity")
    session.add(symbol)
    session.flush()
    return symbol


def add_fact(session, symbol, concept, value, period_end, filed, accession):  # noqa: F811
    session.add(
        Fundamental(
            symbol_id=symbol.id, concept=concept, tag=concept.title(), unit="USD",
            period_end=date.fromisoformat(period_end), value=value,
            filed=date.fromisoformat(filed), accession=accession, form="10-Q",
        )
    )
    session.flush()


def test_a_figure_is_invisible_before_it_was_filed(session):  # noqa: F811
    """The core defence. Q4 ends 31 December; the 10-K lands in February. A
    screen run in January must not see it."""
    symbol = add_symbol(session)
    add_fact(session, symbol, "assets", 100.0, "2023-12-31", "2024-02-15", "a1")

    assert fact_as_of(session, symbol.id, "assets", date(2024, 1, 15)) is None
    assert fact_as_of(session, symbol.id, "assets", date(2024, 2, 15)).value == 100.0


def test_the_most_recent_filed_period_wins(session):  # noqa: F811
    symbol = add_symbol(session)
    add_fact(session, symbol, "assets", 100.0, "2023-12-31", "2024-02-15", "a1")
    add_fact(session, symbol, "assets", 120.0, "2024-03-31", "2024-05-01", "a2")

    assert fact_as_of(session, symbol.id, "assets", date(2024, 4, 1)).value == 100.0
    assert fact_as_of(session, symbol.id, "assets", date(2024, 6, 1)).value == 120.0


def test_a_restatement_filed_later_is_not_visible_earlier(session):  # noqa: F811
    """The subtle one. The revised figure exists in the database, attached to a
    period that has already passed. Keying on period_end would return it."""
    symbol = add_symbol(session)
    add_fact(session, symbol, "assets", 100.0, "2023-12-31", "2024-02-15", "orig")
    add_fact(session, symbol, "assets", 90.0, "2023-12-31", "2024-11-01", "restated")

    assert fact_as_of(session, symbol.id, "assets", date(2024, 5, 1)).value == 100.0


def test_a_restatement_already_public_is_used(session):  # noqa: F811
    """The mirror case, and the reason 'always use the original' would be
    wrong: by December the market had seen the correction."""
    symbol = add_symbol(session)
    add_fact(session, symbol, "assets", 100.0, "2023-12-31", "2024-02-15", "orig")
    add_fact(session, symbol, "assets", 90.0, "2023-12-31", "2024-11-01", "restated")

    assert fact_as_of(session, symbol.id, "assets", date(2024, 12, 1)).value == 90.0


def test_the_accession_of_the_answer_is_returned(session):  # noqa: F811
    """So a surprising screen result can be traced to the filing it rests on."""
    symbol = add_symbol(session)
    add_fact(session, symbol, "assets", 100.0, "2023-12-31", "2024-02-15", "0001-24-000123")

    assert fact_as_of(
        session, symbol.id, "assets", date(2024, 3, 1)
    ).accession == "0001-24-000123"


def test_reporting_lag_is_exposed(session):  # noqa: F811
    symbol = add_symbol(session)
    add_fact(session, symbol, "assets", 100.0, "2023-12-31", "2024-02-15", "a1")

    assert fact_as_of(session, symbol.id, "assets", date(2024, 3, 1)).lag_days == 46


def test_a_missing_concept_is_absent_not_zero(session):  # noqa: F811
    """Zero-filling turns 'we do not know' into a number that flows into a
    ratio and out into a ranking."""
    symbol = add_symbol(session)
    add_fact(session, symbol, "assets", 100.0, "2023-12-31", "2024-02-15", "a1")

    found = facts_as_of(session, symbol.id, ["assets", "liabilities"], date(2024, 3, 1))

    assert set(found) == {"assets"}
    assert "liabilities" not in found


def test_history_can_return_originals_only(session):  # noqa: F811
    """A study of revisions wants the first version of each period. A screen
    does not -- these are different questions and the flag keeps them apart."""
    symbol = add_symbol(session)
    add_fact(session, symbol, "assets", 100.0, "2023-12-31", "2024-02-15", "orig")
    add_fact(session, symbol, "assets", 90.0, "2023-12-31", "2024-11-01", "restated")

    assert len(history(session, symbol.id, "assets")) == 2
    originals = history(session, symbol.id, "assets", original_only=True)
    assert [r.value for r in originals] == [100.0]


def test_facts_from_another_symbol_are_never_returned(session):  # noqa: F811
    a, b = add_symbol(session, "AAA"), add_symbol(session, "BBB")
    add_fact(session, b, "assets", 999.0, "2023-12-31", "2024-02-15", "b1")

    assert fact_as_of(session, a.id, "assets", date(2024, 6, 1)) is None
