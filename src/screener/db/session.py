"""Engine and session management."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings
from .models import Base

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def get_engine(url: str | None = None, echo: bool = False) -> Engine:
    global _engine, _SessionFactory
    if url is not None:
        return create_engine(url, echo=echo, future=True)
    if _engine is None:
        _engine = create_engine(get_settings().database_url, echo=echo, future=True)
        _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionFactory
    if _SessionFactory is None:
        get_engine()
    assert _SessionFactory is not None
    return _SessionFactory


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope. Commits on success, rolls back on any exception."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Columns added after a table first shipped. `create_all` never alters an
# existing table, so each is added here, idempotently, on `db init`. No Alembic
# directory exists in this repository despite the docstring below once saying
# so; this list is the migration path until one does.
_ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    # 2026-09-19: one-sided p against random names on the same days. The Holm
    # correction over validation needs every run's p-value as recorded, not
    # re-derived later from a different seed.
    ("research_runs", "same_day_p", "DOUBLE PRECISION"),
    # 2026-09-19: ticker identity. A backtest joins membership to prices by
    # ticker, and tickers get reused -- BBBY held Overstock's history. An ISIN
    # names the security rather than the letters.
    ("symbols", "isin", "VARCHAR(12)"),
    ("symbols", "security_type", "VARCHAR(40)"),
)


def create_all(engine: Engine) -> None:
    """Create missing tables, then add any column listed in _ADDED_COLUMNS
    that an existing table lacks. Safe to re-run."""
    from sqlalchemy import inspect, text

    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, column, sql_type in _ADDED_COLUMNS:
            if not inspector.has_table(table):
                continue
            present = {c["name"] for c in inspector.get_columns(table)}
            if column not in present:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))
