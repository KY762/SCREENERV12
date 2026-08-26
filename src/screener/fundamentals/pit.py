"""Point-in-time retrieval.

One function decides what was knowable on a given date, so the rule cannot be
implemented correctly in one place and wrongly in another.

The rule
--------
As of date D, the answer is the value from the most recent filing whose
``filed <= D``, for the most recent period whose numbers had been filed by then.

That single filter handles restatements without a second rule. A restatement
filed BEFORE D was public knowledge on D, so it should be used. A restatement
filed AFTER D was not, so it is excluded automatically. There is no need to
prefer "the original" -- preferring it would actually be wrong, because it
would ignore a correction the market had already seen.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Fundamental


@dataclass(frozen=True)
class Reported:
    concept: str
    value: float
    period_end: date
    filed: date
    accession: str
    unit: str

    @property
    def lag_days(self) -> int:
        """How stale the figure was when used. Large lags are normal for
        annual filings and worth seeing rather than assuming."""
        return (self.filed - self.period_end).days


def fact_as_of(
    session: Session,
    symbol_id: int,
    concept: str,
    as_of: date,
    *,
    unit: str | None = None,
) -> Reported | None:
    """The value for ``concept`` that was public on ``as_of``, or None."""
    stmt = (
        select(Fundamental)
        .where(
            Fundamental.symbol_id == symbol_id,
            Fundamental.concept == concept,
            Fundamental.filed <= as_of,
        )
        # Most recent period first; within a period, the most recently filed
        # version -- which is the correction the market had seen by then.
        .order_by(Fundamental.period_end.desc(), Fundamental.filed.desc())
        .limit(1)
    )
    if unit is not None:
        stmt = stmt.where(Fundamental.unit == unit)

    row = session.scalars(stmt).first()
    if row is None:
        return None
    return Reported(
        concept=row.concept,
        value=row.value,
        period_end=row.period_end,
        filed=row.filed,
        accession=row.accession,
        unit=row.unit,
    )


def facts_as_of(
    session: Session, symbol_id: int, concepts: list[str], as_of: date
) -> dict[str, Reported]:
    """Several concepts at once. Missing ones are absent, never zero.

    Zero-filling a missing balance-sheet item silently turns "we do not know"
    into a number that flows into a ratio and out into a ranking.
    """
    found = {}
    for concept in concepts:
        value = fact_as_of(session, symbol_id, concept, as_of)
        if value is not None:
            found[concept] = value
    return found


def history(
    session: Session, symbol_id: int, concept: str, *, original_only: bool = False
) -> list[Reported]:
    """Every stored version of a concept, oldest period first.

    ``original_only`` keeps the first filing of each period, which is what a
    study of revisions needs -- not what a point-in-time screen needs.
    """
    rows = session.scalars(
        select(Fundamental)
        .where(Fundamental.symbol_id == symbol_id, Fundamental.concept == concept)
        .order_by(Fundamental.period_end, Fundamental.filed)
    ).all()

    if original_only:
        seen: set[date] = set()
        rows = [r for r in rows if not (r.period_end in seen or seen.add(r.period_end))]

    return [
        Reported(r.concept, r.value, r.period_end, r.filed, r.accession, r.unit)
        for r in rows
    ]
