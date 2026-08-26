"""Fundamentals ingestion.

One request per company returns its entire filing history, so this is slow but
runs once. Re-running writes only what is new, keyed on the accession number --
which is what makes restatements land as additional rows rather than
overwriting the figure that was public at the time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Fundamental, Symbol
from ..providers.base import ProviderError

log = logging.getLogger(__name__)


@dataclass
class SymbolFacts:
    ticker: str
    written: int = 0
    skipped: int = 0
    concepts: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class FactsSummary:
    results: list[SymbolFacts] = field(default_factory=list)

    @property
    def written(self) -> int:
        return sum(r.written for r in self.results)

    @property
    def failed(self) -> list[SymbolFacts]:
        return [r for r in self.results if not r.ok]

    def summary(self) -> str:
        ok = len(self.results) - len(self.failed)
        return f"{ok}/{len(self.results)} symbols, {self.written:,} fact(s) written"


def ingest_fundamentals(
    session: Session, provider, tickers: list[str]
) -> FactsSummary:
    summary = FactsSummary()

    for ticker in [t.strip().upper() for t in tickers if t.strip()]:
        result = SymbolFacts(ticker=ticker)
        symbol = session.scalar(select(Symbol).where(Symbol.ticker == ticker))
        if symbol is None:
            result.error = "not ingested — run 'screener ingest' first"
            summary.results.append(result)
            continue

        try:
            facts = provider.get_company_facts(ticker)
        except ProviderError as exc:
            result.error = str(exc)
            summary.results.append(result)
            continue

        existing = {
            (row.concept, row.period_end, row.accession, row.unit)
            for row in session.scalars(
                select(Fundamental).where(Fundamental.symbol_id == symbol.id)
            )
        }

        for fact in facts:
            key = (fact.concept, fact.period_end, fact.accession, fact.unit)
            if key in existing:
                result.skipped += 1
                continue
            existing.add(key)
            session.add(
                Fundamental(
                    symbol_id=symbol.id,
                    concept=fact.concept,
                    tag=fact.tag,
                    unit=fact.unit,
                    period_end=fact.period_end,
                    value=fact.value,
                    filed=fact.filed,
                    accession=fact.accession,
                    form=fact.form or None,
                    fiscal_year=fact.fiscal_year,
                    fiscal_period=fact.fiscal_period,
                )
            )
            result.written += 1

        result.concepts = len({f.concept for f in facts})
        session.flush()
        summary.results.append(result)

    return summary
