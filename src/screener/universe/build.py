"""Point-in-time universe construction.

Evaluates eligibility per trading date from stored metrics and persists the
result to ``universe_snapshots``, so a backtest reads the universe as it was
rather than as it is.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db.models import MetricsDaily, PriceDaily, Symbol, UniverseSnapshot
from .definition import UniverseDefinition, passes_static_filters

log = logging.getLogger(__name__)


@dataclass
class UniverseBuildResult:
    definition: UniverseDefinition
    dates_evaluated: int
    memberships_written: int
    symbols_considered: int
    symbols_excluded_static: dict[str, str]

    def summary(self) -> str:
        return (
            f"{self.definition.name}/{self.definition.version}: "
            f"{self.memberships_written:,} membership row(s) across "
            f"{self.dates_evaluated} date(s); "
            f"{len(self.symbols_excluded_static)} symbol(s) excluded outright"
        )


def eligible_frame(
    metrics: pd.DataFrame, closes: pd.Series, definition: UniverseDefinition
) -> pd.Series:
    """Boolean eligibility per date for one symbol.

    Requires BOTH a computable dollar-volume figure and enough history. A NaN
    dollar volume means the 50-day window is not yet full, which is itself a
    failure of the history requirement -- treating NaN as "passes" would admit
    symbols on their first day of trading.
    """
    if metrics.empty or closes.empty:
        return pd.Series(dtype="bool")

    aligned_close = closes.reindex(metrics.index)
    dollar_vol = metrics.get("dollar_vol_50")
    if dollar_vol is None:
        return pd.Series(False, index=metrics.index)

    price_ok = aligned_close >= definition.min_price
    liquidity_ok = dollar_vol >= definition.min_dollar_volume

    bar_number = pd.Series(range(1, len(metrics) + 1), index=metrics.index)
    history_ok = bar_number >= definition.min_history_days

    return (price_ok & liquidity_ok & history_ok).fillna(False)


def build_universe(
    session: Session,
    definition: UniverseDefinition | None = None,
    *,
    start: date | None = None,
    end: date | None = None,
    rebuild: bool = False,
) -> UniverseBuildResult:
    """Evaluate and persist universe membership across the stored date range."""
    definition = definition or UniverseDefinition()
    symbols = list(session.scalars(select(Symbol).order_by(Symbol.ticker)))

    excluded: dict[str, str] = {}
    eligible_symbols: list[Symbol] = []
    for symbol in symbols:
        ok, reason = passes_static_filters(
            definition,
            ticker=symbol.ticker,
            asset_type=symbol.asset_type,
            name=symbol.name,
        )
        if ok:
            eligible_symbols.append(symbol)
        else:
            excluded[symbol.ticker] = reason or "excluded"

    if rebuild:
        stmt = delete(UniverseSnapshot).where(UniverseSnapshot.name == definition.name)
        if start is not None:
            stmt = stmt.where(UniverseSnapshot.date >= start)
        if end is not None:
            stmt = stmt.where(UniverseSnapshot.date <= end)
        session.execute(stmt)
        session.flush()

    existing = {
        (row.date, row.symbol_id)
        for row in session.scalars(
            select(UniverseSnapshot).where(UniverseSnapshot.name == definition.name)
        )
    }

    written = 0
    all_dates: set[date] = set()

    for symbol in eligible_symbols:
        metrics = _load_metrics(session, symbol.id, start, end)
        if metrics.empty:
            continue
        closes = _load_closes(session, symbol.id, start, end)
        mask = eligible_frame(metrics, closes, definition)

        for trade_date in mask.index[mask.to_numpy(dtype=bool)]:
            as_date = trade_date.date() if hasattr(trade_date, "date") else trade_date
            all_dates.add(as_date)
            if (as_date, symbol.id) in existing:
                continue
            session.add(
                UniverseSnapshot(
                    name=definition.name,
                    date=as_date,
                    symbol_id=symbol.id,
                    definition_version=definition.version,
                )
            )
            written += 1
        session.flush()

    return UniverseBuildResult(
        definition=definition,
        dates_evaluated=len(all_dates),
        memberships_written=written,
        symbols_considered=len(symbols),
        symbols_excluded_static=excluded,
    )


def universe_members(
    session: Session, name: str, on_date: date
) -> list[str]:
    """Tickers eligible on a specific date. This is what a backtest must call."""
    rows = session.execute(
        select(Symbol.ticker)
        .join(UniverseSnapshot, UniverseSnapshot.symbol_id == Symbol.id)
        .where(UniverseSnapshot.name == name, UniverseSnapshot.date == on_date)
        .order_by(Symbol.ticker)
    ).all()
    return [r[0] for r in rows]


def _load_metrics(
    session: Session, symbol_id: int, start: date | None, end: date | None
) -> pd.DataFrame:
    stmt = select(MetricsDaily.date, MetricsDaily.dollar_vol_50).where(
        MetricsDaily.symbol_id == symbol_id
    )
    if start is not None:
        stmt = stmt.where(MetricsDaily.date >= start)
    if end is not None:
        stmt = stmt.where(MetricsDaily.date <= end)
    rows = session.execute(stmt.order_by(MetricsDaily.date)).all()
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows, columns=["date", "dollar_vol_50"]).set_index("date")
    frame.index = pd.to_datetime(frame.index)
    return frame


def _load_closes(
    session: Session, symbol_id: int, start: date | None, end: date | None
) -> pd.Series:
    stmt = select(PriceDaily.date, PriceDaily.close).where(
        PriceDaily.symbol_id == symbol_id
    )
    if start is not None:
        stmt = stmt.where(PriceDaily.date >= start)
    if end is not None:
        stmt = stmt.where(PriceDaily.date <= end)
    rows = session.execute(stmt.order_by(PriceDaily.date)).all()
    if not rows:
        return pd.Series(dtype="float64")
    series = pd.Series(
        [float(r[1]) for r in rows], index=pd.to_datetime([r[0] for r in rows])
    )
    return series
