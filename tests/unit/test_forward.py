"""The forward test's one evidential property: the decision predates the outcome.

What breaks if these fail: a paper book that looks like a forward test and is
actually a backtest. A rewritten signal, a silently duplicated one, or a
backfill that does not announce itself all destroy the only thing a forward
test has over a backtest.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from screener.backtest.engine import Candidate
from screener.db.models import PaperSignal
from screener.db.session import create_all
from screener.forward import (
    backfilled,
    load_signals,
    record_signals,
    span,
)
from screener.ingest.prices import get_or_create_symbol

HASH = "a" * 64
OTHER = "b" * 64


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://")
    create_all(engine)
    with Session(engine) as s:
        for ticker in ("AAPL", "MSFT", "NVDA"):
            get_or_create_symbol(s, ticker, asset_type="equity")
        s.flush()
        yield s


def candidate(ticker="AAPL", day=date(2026, 9, 21), stop=95.0, rank=1.0):
    return Candidate(
        ticker=ticker,
        setup="relative_strength",
        signal_date=day,
        entry_date=day + timedelta(days=1),
        stop_distance=stop,
        atr=2.5,
        rank=rank,
    )


# --- recording -------------------------------------------------------------


def test_a_signal_is_written_once(session):
    first = record_signals(
        session, [candidate()], hypothesis="h1", config_hash=HASH
    )
    second = record_signals(
        session, [candidate()], hypothesis="h1", config_hash=HASH
    )

    assert first.written == 1
    assert second.written == 0
    assert second.already_known == 1
    assert session.scalar(select(PaperSignal.id).where(PaperSignal.config_hash == HASH))


def test_rerunning_does_not_rewrite_what_was_recorded(session):
    """The property the whole module exists for. If a re-run could overwrite a
    signal, nothing here would predate its outcome and the book would be a
    backtest with extra steps."""
    record_signals(session, [candidate(stop=95.0)], hypothesis="h1", config_hash=HASH)
    original = session.scalars(select(PaperSignal)).one()
    written_at, stop_was = original.recorded_at, original.stop_distance

    record_signals(session, [candidate(stop=42.0)], hypothesis="h1", config_hash=HASH)

    after = session.scalars(select(PaperSignal)).one()
    assert after.recorded_at == written_at
    assert after.stop_distance == stop_was


def test_the_same_symbol_twice_in_one_batch_does_not_roll_the_run_back(session):
    """A duplicate key rolled back a 307-symbol ingest once, and reported
    success while doing it. The seen-set has to grow as the batch is written."""
    result = record_signals(
        session, [candidate(), candidate()], hypothesis="h1", config_hash=HASH
    )

    assert result.written == 1
    assert len(session.scalars(select(PaperSignal)).all()) == 1


def test_two_configurations_keep_two_books(session):
    """A book is keyed by the run identity. Two configurations sharing one book
    would mix trades from rules that were never the same rule."""
    record_signals(session, [candidate()], hypothesis="h1", config_hash=HASH)
    record_signals(session, [candidate()], hypothesis="h1", config_hash=OTHER)

    assert span(session, HASH).signals == 1
    assert span(session, OTHER).signals == 1


def test_since_keeps_a_first_run_from_backfilling_everything(session):
    old = candidate(day=date(2012, 3, 1))
    new = candidate(day=date(2026, 9, 21))

    result = record_signals(
        session, [old, new], hypothesis="h1", config_hash=HASH,
        since=date(2026, 1, 1),
    )

    assert result.written == 1
    assert result.considered == 1


def test_a_signal_for_an_unknown_symbol_is_reported_not_silently_dropped(session):
    result = record_signals(
        session, [candidate(ticker="NOPE")], hypothesis="h1", config_hash=HASH
    )

    assert result.written == 0
    assert result.no_symbol == ["NOPE"]


# --- reading back ----------------------------------------------------------


def test_signals_come_back_as_engine_candidates(session):
    """The book is derived by `run_backtest`, so what is stored has to
    reconstruct into the engine's own type without a translation layer that
    could drift."""
    record_signals(session, [candidate(stop=95.0, rank=3.5)], hypothesis="h1", config_hash=HASH)

    (back,) = load_signals(session, HASH)

    assert isinstance(back, Candidate)
    assert back.ticker == "AAPL"
    assert back.stop_distance == pytest.approx(95.0)
    assert back.rank == pytest.approx(3.5)
    assert back.entry_date > back.signal_date


def test_signals_are_ordered_oldest_first(session):
    for day in (date(2026, 9, 18), date(2026, 9, 16), date(2026, 9, 17)):
        record_signals(session, [candidate(day=day)], hypothesis="h1", config_hash=HASH)

    assert [c.signal_date for c in load_signals(session, HASH)] == [
        date(2026, 9, 16), date(2026, 9, 17), date(2026, 9, 18),
    ]


# --- the backfill warning --------------------------------------------------


def test_a_book_seeded_from_history_is_flagged_as_backfilled(session):
    """Seeding from history is a reasonable way to start, and it is not a
    forward test. Anything reporting on such a book has to say so, or a
    backtest gets read as prospective evidence."""
    record_signals(
        session, [candidate(day=date(2012, 3, 1))], hypothesis="h1", config_hash=HASH
    )

    assert backfilled(span(session, HASH))


def test_a_book_recorded_as_it_happened_is_not_flagged(session):
    """Signals written on the day they were produced -- the real thing."""
    record_signals(session, [candidate(day=date.today())], hypothesis="h1", config_hash=HASH)

    assert not backfilled(span(session, HASH))


def test_an_empty_book_is_not_a_backfill(session):
    assert not backfilled(span(session, HASH))
    assert span(session, HASH).describe() == "no signals recorded yet"


def test_the_span_reports_when_rows_were_written_not_just_their_dates(session):
    """The recorded date is the evidential column: it is what separates a
    signal that predated its outcome from one that did not."""
    record_signals(session, [candidate(day=date(2026, 9, 21))], hypothesis="h1", config_hash=HASH)

    book = span(session, HASH)

    assert book.first_signal == date(2026, 9, 21)
    assert book.recorded_first == datetime.now(UTC).date()
