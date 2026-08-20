"""Metrics computation: price_daily -> metrics_daily.

Two-pass by necessity. Pass one computes everything derivable from a single
symbol's own bars. Pass two computes relative strength, which needs the
benchmark's returns aligned to the same dates and therefore cannot be done
while iterating symbols independently.

metrics_daily is a CACHE. Every column is reproducible from price_daily, so a
rebuild is always safe and a corrupted row is never a data loss.

Warmup handling
---------------
Metrics are NaN until enough history exists, and NaN is written as NULL rather
than filled. A back-filled moving average is fabricated history, and it would
make a backtest trade on information that did not exist.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..calc import indicators as ind
from ..calc.relative_strength import relative_strength, relative_strength_adjusted
from ..db.models import MetricsDaily, PriceDaily, Symbol

log = logging.getLogger(__name__)

RS_LOOKBACK = 63          # [CONVENTION] ~3 months, the H1 baseline
MIN_BARS_REQUIRED = 20    # below this nothing meaningful is computable


@dataclass
class MetricsResult:
    ticker: str
    rows_written: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def load_bars(session: Session, symbol_id: int) -> pd.DataFrame:
    """Load a symbol's full raw history as a DataFrame indexed by date."""
    rows = session.execute(
        select(
            PriceDaily.date, PriceDaily.open, PriceDaily.high,
            PriceDaily.low, PriceDaily.close, PriceDaily.volume,
        )
        .where(PriceDaily.symbol_id == symbol_id)
        .order_by(PriceDaily.date)
    ).all()
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    frame = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    frame = frame.set_index("date")
    frame.index = pd.to_datetime(frame.index)
    return frame.astype("float64").sort_index()


def compute_metrics_frame(bars: pd.DataFrame) -> pd.DataFrame:
    """Single-symbol metrics. Pure: DataFrame in, DataFrame out.

    Every column delegates to the tested calc layer rather than reimplementing
    arithmetic here -- the golden-value and no-lookahead guarantees live there,
    and duplicating the maths would put them out of reach.
    """
    if bars.empty:
        return pd.DataFrame()

    close = bars["close"]
    sma_50 = ind.sma(close, 50)
    sma_200 = ind.sma(close, 200)

    out = pd.DataFrame(index=bars.index)
    out["sma_20"] = ind.sma(close, 20)
    out["sma_50"] = sma_50
    out["sma_200"] = sma_200
    out["sma_200_rising"] = ind.slope_positive(sma_200, 21)
    out["ma_aligned"] = ((close > sma_50) & (sma_50 > sma_200)).where(
        close.notna() & sma_50.notna() & sma_200.notna()
    ).astype("boolean")

    out["atr_14"] = ind.atr(bars, 14)
    out["atr_pct_14"] = ind.atr_pct(bars, 14)
    out["realized_vol_63"] = ind.realized_vol(close, 63)

    for period in (5, 21, 63, 126, 252):
        out[f"ret_{period}"] = ind.returns(close, period)

    out["rvol_20"] = ind.rvol(bars, 20)
    out["clv"] = ind.clv(bars)
    out["pct_from_252d_high"] = ind.pct_from_high(bars, 252)
    out["dollar_vol_50"] = ind.dollar_volume(bars, 50)
    return out


def compute_relative_strength_frame(
    bars: pd.DataFrame, benchmark: pd.DataFrame, lookback: int = RS_LOOKBACK
) -> pd.DataFrame:
    """Relative strength against a benchmark, aligned on shared dates only.

    Dates the benchmark lacks yield NaN rather than a silently mismatched
    comparison -- comparing a symbol's Tuesday to the benchmark's Monday would
    manufacture strength that never existed.
    """
    if bars.empty or benchmark.empty:
        return pd.DataFrame()
    out = pd.DataFrame(index=bars.index)
    out[f"rs_{lookback}"] = relative_strength(bars["close"], benchmark["close"], lookback)
    out[f"rs_adj_{lookback}"] = relative_strength_adjusted(
        bars["close"], benchmark["close"], lookback
    )
    return out.reindex(bars.index)


def build_metrics(
    session: Session,
    tickers: list[str] | None = None,
    *,
    benchmark_ticker: str = "SPY",
    rebuild: bool = False,
    since: date | None = None,
) -> list[MetricsResult]:
    """Compute and persist metrics for the given symbols (or all of them).

    ``rebuild=True`` deletes existing rows first. Otherwise rows are upserted,
    so an interrupted run can simply be re-run.

    ``since`` limits which rows are WRITTEN, never which are computed. Metrics
    depend on long history -- a 200-day average needs 200 prior bars -- so the
    full series is always computed and only the tail is persisted. This is what
    makes a nightly update cheap: one new bar per symbol writes one row instead
    of rewriting a decade.
    """
    symbols = _resolve_symbols(session, tickers)
    benchmark_bars = _load_benchmark(session, benchmark_ticker)

    results: list[MetricsResult] = []
    for symbol in symbols:
        results.append(
            _build_one(session, symbol, benchmark_bars, rebuild=rebuild, since=since)
        )
    return results


def _resolve_symbols(session: Session, tickers: list[str] | None) -> list[Symbol]:
    stmt = select(Symbol).order_by(Symbol.ticker)
    if tickers:
        stmt = stmt.where(Symbol.ticker.in_([t.strip().upper() for t in tickers]))
    return list(session.scalars(stmt))


def _load_benchmark(session: Session, ticker: str) -> pd.DataFrame:
    symbol = session.scalar(select(Symbol).where(Symbol.ticker == ticker.upper()))
    if symbol is None:
        log.warning(
            "benchmark %s not ingested; relative strength will be NULL", ticker
        )
        return pd.DataFrame()
    return load_bars(session, symbol.id)


def _build_one(
    session: Session,
    symbol: Symbol,
    benchmark: pd.DataFrame,
    *,
    rebuild: bool,
    since: date | None = None,
) -> MetricsResult:
    bars = load_bars(session, symbol.id)
    if len(bars) < MIN_BARS_REQUIRED:
        return MetricsResult(
            symbol.ticker,
            error=f"only {len(bars)} bars stored; need at least {MIN_BARS_REQUIRED}",
        )

    frame = compute_metrics_frame(bars)
    if not benchmark.empty and symbol.ticker != benchmark.attrs.get("ticker"):
        rs = compute_relative_strength_frame(bars, benchmark)
        if not rs.empty:
            frame = frame.join(rs)

    if rebuild:
        session.execute(
            delete(MetricsDaily).where(MetricsDaily.symbol_id == symbol.id)
        )
        session.flush()
    elif since is not None:
        # Compute on full history (needed for the 200-day window), persist only
        # the tail. Nothing is lost: older rows already exist and are unchanged.
        frame = frame.loc[frame.index >= pd.Timestamp(since)]

    written = _upsert_metrics(session, symbol.id, frame)
    return MetricsResult(symbol.ticker, rows_written=written)


_COLUMN_MAP = {
    "sma_20": "sma_20", "sma_50": "sma_50", "sma_200": "sma_200",
    "sma_200_rising": "sma_200_rising", "ma_aligned": "ma_aligned",
    "atr_14": "atr_14", "atr_pct_14": "atr_pct_14",
    "realized_vol_63": "realized_vol_63",
    "ret_5": "ret_5", "ret_21": "ret_21", "ret_63": "ret_63",
    "ret_126": "ret_126", "ret_252": "ret_252",
    "rs_63": "rs_63", "rs_adj_63": "rs_adj_63",
    "rvol_20": "rvol_20", "clv": "clv",
    "pct_from_252d_high": "pct_from_252d_high",
    "dollar_vol_50": "dollar_vol_50",
}


def _upsert_metrics(session: Session, symbol_id: int, frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0

    dates = [d.date() if hasattr(d, "date") else d for d in frame.index]
    existing = {
        row.date: row
        for row in session.scalars(
            select(MetricsDaily).where(
                MetricsDaily.symbol_id == symbol_id, MetricsDaily.date.in_(dates)
            )
        )
    }

    touched = 0
    for idx, row in frame.iterrows():
        trade_date = idx.date() if hasattr(idx, "date") else idx
        values = {
            attr: _clean(row.get(col))
            for col, attr in _COLUMN_MAP.items()
            if col in frame.columns
        }
        current = existing.get(trade_date)
        if current is None:
            session.add(MetricsDaily(symbol_id=symbol_id, date=trade_date, **values))
            touched += 1
        else:
            if any(getattr(current, k) != v for k, v in values.items()):
                for k, v in values.items():
                    setattr(current, k, v)
                touched += 1
    session.flush()
    return touched


def _clean(value):
    """NaN and pandas NA become NULL. A filled warmup value is fabricated history."""
    if value is None or value is pd.NA:
        return None
    if isinstance(value, bool):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None
    if isinstance(value, float) and (math.isinf(value)):
        return None
    return float(value) if not isinstance(value, (int, bool)) else value
