"""The forward test: signals recorded before their outcomes exist.

A backtest asks what a rule would have done. A forward test asks what it does,
and the only thing that makes the second worth more than the first is that the
decision provably predates the outcome. So this module stores exactly one
thing -- the signal, on the day it was produced -- and derives everything else.

WHY NOTHING ELSE IS STORED. The obvious design keeps a table of open positions
and marks them each day: fill here, stop hit there, closed on the time limit.
That is a second implementation of the exit rules, and the moment it disagrees
with `backtest/engine.py` the forward test stops measuring the thing that was
backtested. Instead the stored signals are fed back through `run_backtest`
itself, so the book is produced by the same engine, the same ExitRule, the same
slippage and the same ambiguity convention (non-negotiable 6) as every
development result. There is no second implementation to drift.

WHAT THIS DOES NOT PROVE. A forward test on paper is not a live track record.
It has no queue position, no partial fills, and no emotional cost, and its fills
are the engine's assumption rather than a broker's confirmation. It answers a
narrower question honestly: does the rule, run prospectively on data it has
never seen, keep doing what the development split said it does.

It also spends no split budget, which is the point of having it. Validation and
test are finite and one-way (non-negotiable 5). This is not.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .backtest.engine import Candidate
from .db.models import PaperSignal, Symbol

log = logging.getLogger(__name__)


@dataclass
class RecordResult:
    considered: int = 0
    written: int = 0
    already_known: int = 0
    no_symbol: list[str] | None = None

    def summary(self) -> str:
        return (
            f"{self.written} new signal(s) recorded, "
            f"{self.already_known} already on the book, "
            f"{self.considered} considered"
        )


def record_signals(
    session: Session,
    candidates: list[Candidate],
    *,
    hypothesis: str,
    config_hash: str,
    since: date | None = None,
) -> RecordResult:
    """Append signals to the paper book. Idempotent, and never overwrites.

    Re-running on the same day writes nothing new, so a cron that fires twice
    does not double the book. A row that already exists is left exactly as it
    was written -- rewriting it would destroy the only property that makes this
    a forward test.

    `since` drops signals older than a date, which is what stops a first run
    from back-filling years of history and calling it prospective.
    """
    result = RecordResult(no_symbol=[])
    wanted = [c for c in candidates if since is None or c.signal_date >= since]
    result.considered = len(wanted)
    if not wanted:
        return result

    tickers = {c.ticker for c in wanted}
    by_ticker = {
        s.ticker: s
        for s in session.scalars(select(Symbol).where(Symbol.ticker.in_(tickers)))
    }
    existing = {
        (row.symbol_id, row.signal_date)
        for row in session.scalars(
            select(PaperSignal).where(PaperSignal.config_hash == config_hash)
        )
    }

    for candidate in wanted:
        symbol = by_ticker.get(candidate.ticker)
        if symbol is None:
            result.no_symbol.append(candidate.ticker)
            continue
        key = (symbol.id, candidate.signal_date)
        if key in existing:
            result.already_known += 1
            continue
        # The seen-set grows as the batch is written, so a candidate list that
        # somehow contains the same symbol twice on one day cannot violate the
        # unique constraint and roll the whole run back.
        existing.add(key)
        session.add(PaperSignal(
            symbol_id=symbol.id,
            hypothesis=hypothesis,
            config_hash=config_hash,
            setup=candidate.setup,
            signal_date=candidate.signal_date,
            entry_date=candidate.entry_date,
            stop_level=_money(candidate.stop_level),
            stop_distance=_money(candidate.stop_distance),
            atr=_money(candidate.atr),
            rank=float(candidate.rank),
        ))
        result.written += 1

    if result.written:
        session.flush()
    return result


def load_signals(
    session: Session, config_hash: str, *, prospective_only: bool = False
) -> list[Candidate]:
    """Every recorded signal for one configuration, oldest first.

    Rebuilt into the engine's own `Candidate`, so the book is computed by the
    same code path as a backtest rather than by anything written here.

    `prospective_only` keeps just the rows whose signal date is on or after the
    day they were WRITTEN. Those are the forward test. A row dated before the
    day it was written was seeded from history, and mixing the two produces a
    number that is neither a backtest nor a forward test -- which is worse than
    either, because it reads as the second while containing the first.
    """
    stmt = (
        select(
            Symbol.ticker, PaperSignal.setup, PaperSignal.signal_date,
            PaperSignal.entry_date, PaperSignal.stop_level,
            PaperSignal.stop_distance, PaperSignal.atr, PaperSignal.rank,
        )
        .join(Symbol, Symbol.id == PaperSignal.symbol_id)
        .where(PaperSignal.config_hash == config_hash)
        .order_by(PaperSignal.signal_date, Symbol.ticker)
    )
    if prospective_only:
        stmt = stmt.where(
            PaperSignal.signal_date >= func.date(PaperSignal.recorded_at)
        )
    rows = session.execute(stmt).all()
    return [
        Candidate(
            ticker=ticker,
            setup=setup,
            signal_date=signal_date,
            entry_date=entry_date,
            stop_level=float(stop_level) if stop_level is not None else None,
            stop_distance=float(stop_distance) if stop_distance is not None else None,
            atr=float(atr) if atr is not None else None,
            rank=float(rank),
        )
        for ticker, setup, signal_date, entry_date, stop_level, stop_distance, atr, rank
        in rows
    ]


@dataclass(frozen=True)
class BookSpan:
    """What the paper book covers, for the header of any report about it."""

    signals: int
    first_signal: date | None
    last_signal: date | None
    recorded_first: date | None
    recorded_last: date | None

    def describe(self) -> str:
        if not self.signals:
            return "no signals recorded yet"
        return (
            f"{self.signals:,} signal(s) from {self.first_signal} to "
            f"{self.last_signal}, recorded {self.recorded_first} to "
            f"{self.recorded_last}"
        )


def span(session: Session, config_hash: str) -> BookSpan:
    """The book's extent, including WHEN the rows were written.

    The recorded dates are the evidential part. A signal dated 2016 that was
    written today is a backfill, not a forward test, and the two are only
    distinguishable because this column exists.
    """
    row = session.execute(
        select(
            func.count(PaperSignal.id),
            func.min(PaperSignal.signal_date),
            func.max(PaperSignal.signal_date),
            func.min(PaperSignal.recorded_at),
            func.max(PaperSignal.recorded_at),
        ).where(PaperSignal.config_hash == config_hash)
    ).one()
    count, first, last, rec_first, rec_last = row
    return BookSpan(
        signals=int(count or 0),
        first_signal=first,
        last_signal=last,
        recorded_first=rec_first.date() if rec_first is not None else None,
        recorded_last=rec_last.date() if rec_last is not None else None,
    )


def backfilled(book: BookSpan) -> bool:
    """True when signals predate the day they were written.

    Not an error -- seeding a book from history is a reasonable way to start --
    but a book in that state is a backtest wearing a forward test's clothes,
    and anything reporting on it has to say so.
    """
    if book.last_signal is None or book.recorded_first is None:
        return False
    return book.first_signal < book.recorded_first


def _money(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(round(float(value), 6)))


def latest_bar(bars_by_symbol: dict[str, pd.DataFrame]) -> date | None:
    """The most recent session any symbol has a bar for.

    The book can only be marked to here, and saying so is how a stale data
    pull stops looking like a quiet week.
    """
    stamps = [frame.index.max() for frame in bars_by_symbol.values() if len(frame)]
    if not stamps:
        return None
    newest = max(stamps)
    return newest.date() if hasattr(newest, "date") else newest
