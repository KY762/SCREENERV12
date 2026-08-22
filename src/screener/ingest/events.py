"""Earnings-date ingestion.

Same shape as price ingestion, and for the same reasons: idempotent, one symbol
failing never aborts the run, and everything attempted is recorded whether or
not it succeeded.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import EarningsEvent, Symbol
from ..providers.base import ProviderError

log = logging.getLogger(__name__)


@dataclass
class SymbolEvents:
    ticker: str
    written: int = 0
    skipped: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class EventsSummary:
    results: list[SymbolEvents] = field(default_factory=list)

    @property
    def written(self) -> int:
        return sum(r.written for r in self.results)

    @property
    def failed(self) -> list[SymbolEvents]:
        return [r for r in self.results if not r.ok]

    def summary(self) -> str:
        ok = len(self.results) - len(self.failed)
        return f"{ok}/{len(self.results)} symbols, {self.written} event(s) written"


def ingest_earnings(
    session: Session,
    provider,
    tickers: list[str],
    start: date,
    end: date,
) -> EventsSummary:
    """Fetch and store filing dates. Safe to re-run over any range."""
    summary = EventsSummary()

    for ticker in [t.strip().upper() for t in tickers if t.strip()]:
        result = SymbolEvents(ticker=ticker)
        symbol = session.scalar(select(Symbol).where(Symbol.ticker == ticker))
        if symbol is None:
            result.error = "not ingested — run 'screener ingest' first"
            summary.results.append(result)
            continue

        try:
            filings = provider.get_earnings_dates(ticker, start, end)
        except ProviderError as exc:
            result.error = str(exc)
            summary.results.append(result)
            continue

        existing = {
            (row.filed, row.form)
            for row in session.scalars(
                select(EarningsEvent).where(EarningsEvent.symbol_id == symbol.id)
            )
        }
        for filing in filings:
            if (filing.filed, filing.form) in existing:
                result.skipped += 1
                continue
            session.add(
                EarningsEvent(
                    symbol_id=symbol.id,
                    filed=filing.filed,
                    form=filing.form,
                    period=filing.period,
                    accession=filing.accession or None,
                    source=getattr(provider, "name", "edgar"),
                )
            )
            result.written += 1
        session.flush()
        summary.results.append(result)

    return summary


def earnings_dates(session: Session, symbol_id: int) -> list[date]:
    """Stored filing dates for one symbol, oldest first."""
    return list(
        session.scalars(
            select(EarningsEvent.filed)
            .where(EarningsEvent.symbol_id == symbol_id)
            .order_by(EarningsEvent.filed)
        )
    )
