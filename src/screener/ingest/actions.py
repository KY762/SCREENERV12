"""Corporate action ingestion.

The table existed from the first migration and held zero rows until
2026-09-19, which meant the "adjusted series derived on demand" half of
non-negotiable 2 had nothing to derive from. See `calc/splits.py` for what
that cost.

Only splits are fetched. Dividends are a different question -- total return --
and adjusting a price a backtest fills at for them would misstate the fill.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..calc.splits import Split
from ..db.models import CorporateAction, Symbol
from ..providers.base import ProviderError

log = logging.getLogger(__name__)


@dataclass
class ActionIngestResult:
    symbols_checked: int = 0
    symbols_with_splits: int = 0
    actions_written: int = 0
    failures: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"{self.actions_written:,} split(s) written across "
            f"{self.symbols_with_splits:,} of {self.symbols_checked:,} symbol(s); "
            f"{len(self.failures)} failure(s)"
        )


def ingest_splits(
    session: Session,
    provider,
    tickers: list[str],
    *,
    start: date,
    end: date,
    progress=None,
) -> ActionIngestResult:
    """Fetch and store splits for each ticker.

    Idempotent on `(symbol_id, ex_date, action_type)`: a re-run writes nothing
    new, so an interrupted pass resumes by being run again.

    One symbol's failure is recorded and the pass continues. The opposite --
    letting one 404 abort the batch -- is a bug this project has already made
    once, on this same provider, where the error was then attributed to all 866
    symbols.
    """
    result = ActionIngestResult()
    by_ticker = {
        s.ticker: s for s in session.scalars(select(Symbol).where(Symbol.ticker.in_(tickers)))
    }

    for ticker in tickers:
        result.symbols_checked += 1
        if progress is not None:
            progress(ticker, result)
        symbol = by_ticker.get(ticker)
        if symbol is None:
            result.failures[ticker] = "no symbol row"
            continue
        try:
            actions = provider.get_corporate_actions(ticker, start, end)
        except ProviderError as exc:
            result.failures[ticker] = str(exc)
            continue
        except Exception as exc:                      # noqa: BLE001 - see docstring
            result.failures[ticker] = f"{type(exc).__name__}: {exc}"
            continue

        if not actions:
            continue

        existing = {
            row.ex_date
            for row in session.scalars(
                select(CorporateAction).where(
                    CorporateAction.symbol_id == symbol.id,
                    CorporateAction.action_type == "split",
                )
            )
        }
        wrote = 0
        for action in actions:
            if action.ex_date in existing:
                continue
            # The seen-set grows as the batch is written. A provider that
            # returns the same ex-date twice would otherwise violate the unique
            # constraint and roll the whole pass back -- the exact shape of the
            # duplicate-key bug found on 2026-09-17.
            existing.add(action.ex_date)
            session.add(CorporateAction(
                symbol_id=symbol.id,
                ex_date=action.ex_date,
                action_type="split",
                ratio=Decimal(str(action.ratio)) if action.ratio is not None else None,
                source=getattr(provider, "name", "unknown"),
            ))
            wrote += 1
        if wrote:
            session.flush()
            result.actions_written += wrote
        if actions:
            result.symbols_with_splits += 1

    return result


def load_splits(session: Session, symbol_id: int) -> list[Split]:
    """Stored splits for one symbol, oldest first, ready for `adjust_bars`."""
    rows = session.execute(
        select(CorporateAction.ex_date, CorporateAction.ratio)
        .where(
            CorporateAction.symbol_id == symbol_id,
            CorporateAction.action_type == "split",
        )
        .order_by(CorporateAction.ex_date)
    ).all()
    return [
        Split(ex_date=ex_date, ratio=float(ratio))
        for ex_date, ratio in rows
        if ratio is not None and float(ratio) > 0
    ]


def load_splits_bulk(session: Session) -> dict[int, list[Split]]:
    """Every symbol's splits in one query.

    A per-symbol query inside a 1,000-symbol load is 1,000 round trips for a
    table with a few thousand rows in it.
    """
    rows = session.execute(
        select(CorporateAction.symbol_id, CorporateAction.ex_date, CorporateAction.ratio)
        .where(CorporateAction.action_type == "split")
        .order_by(CorporateAction.symbol_id, CorporateAction.ex_date)
    ).all()
    out: dict[int, list[Split]] = {}
    for symbol_id, ex_date, ratio in rows:
        if ratio is None or float(ratio) <= 0:
            continue
        out.setdefault(symbol_id, []).append(Split(ex_date=ex_date, ratio=float(ratio)))
    return out
