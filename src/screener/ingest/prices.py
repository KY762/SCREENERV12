"""Daily bar ingestion: provider -> validation -> database.

Idempotency is the central requirement. Re-running the same date range must
converge on the same rows, never duplicate them. Two mechanisms enforce it:
the composite primary key ``(symbol_id, date)`` on ``price_daily``, and the
read-then-split upsert below.

That property is what makes a missed nightly run recoverable by simply running
it again -- which matters because the platform runs on a laptop that is not
always awake.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import DataQualityLog, IngestionRun, PriceDaily, Symbol
from ..providers.base import BarRequest, PriceProvider, ProviderError
from ..validate.rules import ValidationReport, validate_bars

log = logging.getLogger(__name__)


@dataclass
class SymbolResult:
    ticker: str
    rows_written: int = 0
    rows_quarantined: int = 0
    error: str | None = None
    report: ValidationReport | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class IngestionSummary:
    run_id: int | None
    requested: int
    results: list[SymbolResult] = field(default_factory=list)

    @property
    def succeeded(self) -> list[SymbolResult]:
        return [r for r in self.results if r.ok]

    @property
    def failed(self) -> list[SymbolResult]:
        return [r for r in self.results if not r.ok]

    @property
    def rows_written(self) -> int:
        return sum(r.rows_written for r in self.results)

    @property
    def status(self) -> str:
        if not self.failed:
            return "succeeded"
        return "failed" if not self.succeeded else "partial"

    def summary(self) -> str:
        return (
            f"{len(self.succeeded)}/{self.requested} symbols ok, "
            f"{self.rows_written} rows written, {len(self.failed)} failed"
        )


def get_or_create_symbol(session: Session, ticker: str, **defaults) -> Symbol:
    """Look up a symbol by ticker, creating it if absent."""
    ticker = ticker.strip().upper()
    symbol = session.scalar(select(Symbol).where(Symbol.ticker == ticker))
    if symbol is None:
        symbol = Symbol(ticker=ticker, **defaults)
        session.add(symbol)
        session.flush()
    return symbol


def ingest_daily_bars(
    session: Session,
    provider: PriceProvider,
    tickers: list[str],
    start: date,
    end: date,
    *,
    expected_sessions: pd.DatetimeIndex | None = None,
    job: str = "daily_bars",
) -> IngestionSummary:
    """Fetch, validate, and persist daily bars for ``tickers``.

    A symbol that fails does not abort the run -- the failure is recorded and
    the remaining symbols proceed. One misbehaving ticker must never take down
    a nightly job.
    """
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    run = IngestionRun(
        job=job,
        provider=getattr(provider, "name", "unknown"),
        range_start=start,
        range_end=end,
        symbols_requested=len(tickers),
        status="running",
    )
    session.add(run)
    session.flush()

    summary = IngestionSummary(run_id=run.id, requested=len(tickers))

    try:
        frame = provider.get_daily_bars(
            BarRequest(symbols=tuple(tickers), start=start, end=end, adjustment="raw")
        )
    except ProviderError as exc:
        run.status = "failed"
        run.finished_at = datetime.now(UTC)
        run.error = str(exc)
        session.flush()
        summary.results = [SymbolResult(t, error=str(exc)) for t in tickers]
        return summary

    for ticker in tickers:
        result = _ingest_one(session, run, frame, ticker, provider, expected_sessions)
        summary.results.append(result)

    run.symbols_ok = len(summary.succeeded)
    run.symbols_failed = len(summary.failed)
    run.rows_written = summary.rows_written
    run.status = summary.status
    run.finished_at = datetime.now(UTC)
    session.flush()
    return summary


def _ingest_one(
    session: Session,
    run: IngestionRun,
    frame: pd.DataFrame,
    ticker: str,
    provider: PriceProvider,
    expected_sessions: pd.DatetimeIndex | None,
) -> SymbolResult:
    try:
        bars = _slice_symbol(frame, ticker)
    except KeyError:
        return SymbolResult(ticker, error="no bars returned by provider")

    if bars.empty:
        return SymbolResult(ticker, error="no bars returned by provider")

    report = validate_bars(ticker, bars, expected_sessions=expected_sessions)
    symbol = get_or_create_symbol(session, ticker)

    for violation in report.violations:
        session.add(
            DataQualityLog(
                run_id=run.id,
                symbol_id=symbol.id,
                ticker=ticker,
                trade_date=violation.trade_date,
                rule=violation.rule,
                severity=str(violation.severity),
                detail=violation.detail,
            )
        )

    quarantined = report.quarantined_dates
    clean = bars[~bars.index.map(lambda d: pd.Timestamp(d).date() in quarantined)]

    if clean.empty:
        return SymbolResult(
            ticker, rows_quarantined=len(quarantined),
            error="every bar failed validation", report=report,
        )

    written = _upsert_bars(session, symbol, clean, source=getattr(provider, "name", "unknown"))
    _refresh_symbol_span(session, symbol)

    return SymbolResult(
        ticker, rows_written=written, rows_quarantined=len(quarantined), report=report
    )


def _slice_symbol(frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Extract one symbol's bars, indexed by date."""
    if isinstance(frame.index, pd.MultiIndex):
        if ticker not in frame.index.get_level_values("symbol"):
            raise KeyError(ticker)
        out = frame.xs(ticker, level="symbol").copy()
    else:
        out = frame.copy()
    out.index = pd.to_datetime(out.index)
    return out.sort_index()


def _upsert_bars(session: Session, symbol: Symbol, bars: pd.DataFrame, source: str) -> int:
    """Insert new bars and update changed ones. Returns rows touched.

    Existing keys are read first, then rows are split into inserts and updates.
    This is portable across Postgres and SQLite, which matters because tests run
    on SQLite while production runs on Postgres -- a dialect-specific upsert
    would leave the tested path different from the deployed one.
    """
    dates = [d.date() if hasattr(d, "date") else d for d in bars.index]
    existing = {
        row.date: row
        for row in session.scalars(
            select(PriceDaily).where(
                PriceDaily.symbol_id == symbol.id, PriceDaily.date.in_(dates)
            )
        )
    }

    touched = 0
    for idx, row in bars.iterrows():
        trade_date = idx.date() if hasattr(idx, "date") else idx
        values = dict(
            open=_dec(row["open"]),
            high=_dec(row["high"]),
            low=_dec(row["low"]),
            close=_dec(row["close"]),
            volume=int(row["volume"]),
            source=source,
        )
        current = existing.get(trade_date)
        if current is None:
            session.add(PriceDaily(symbol_id=symbol.id, date=trade_date, **values))
            touched += 1
        else:
            changed = any(getattr(current, k) != v for k, v in values.items())
            if changed:
                for k, v in values.items():
                    setattr(current, k, v)
                touched += 1
    session.flush()
    return touched


def _refresh_symbol_span(session: Session, symbol: Symbol) -> None:
    """Keep first_date/last_date in step with what is actually stored."""
    from sqlalchemy import func as sqlfunc

    span = session.execute(
        select(sqlfunc.min(PriceDaily.date), sqlfunc.max(PriceDaily.date)).where(
            PriceDaily.symbol_id == symbol.id
        )
    ).one()
    symbol.first_date, symbol.last_date = span[0], span[1]
    session.flush()


def _dec(value) -> Decimal:
    return Decimal(str(round(float(value), 6)))
