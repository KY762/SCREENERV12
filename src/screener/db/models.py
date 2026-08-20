"""Database schema -- Phase 1 subset: the data foundation.

Tables for positions, trades, journal, screens, and AI runs are deliberately
absent. They belong to later phases, and creating tables before the code that
writes to them produces schemas that drift from reality.

Type conventions
----------------
Money and prices are ``Numeric``, never ``Float``. A float is fine for an
indicator; it is not fine for a number that determines how many shares get
bought or what a position is worth.

Trading dates are ``Date`` in exchange-local terms. Wall-clock instants are
``DateTime(timezone=True)`` in UTC. Mixing the two is the usual source of
off-by-one-day errors in returns and "days until earnings".

Adjustment policy
-----------------
``price_daily`` stores RAW, UNADJUSTED bars. Adjustments are derived on demand
from ``corporate_actions``. Storing pre-adjusted prices makes history mutate
under you -- a split today silently rewrites what you believed in 2019 -- which
is a direct route to look-ahead bias in backtests.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

PRICE = Numeric(18, 6)
RATIO = Numeric(18, 8)


class Base(DeclarativeBase):
    pass


class Symbol(Base):
    """Instrument master. One row per tradeable instrument."""

    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    exchange: Mapped[str | None] = mapped_column(String(20))
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False, default="equity")
    sector: Mapped[str | None] = mapped_column(String(100))
    industry: Mapped[str | None] = mapped_column(String(150))
    cik: Mapped[str | None] = mapped_column(String(20), index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    first_date: Mapped[date | None] = mapped_column(Date)
    last_date: Mapped[date | None] = mapped_column(Date)
    delisted_date: Mapped[date | None] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    bars: Mapped[list[PriceDaily]] = relationship(
        back_populates="symbol", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "asset_type IN ('equity','etf','adr','fund')", name="ck_symbols_asset_type"
        ),
    )

    def __repr__(self) -> str:
        return f"<Symbol {self.ticker}>"


class SymbolAlias(Base):
    """Historical ticker symbols, so a rename does not orphan history.

    Without this, a ticker change silently splits one instrument's history into
    two partial records, and any backtest spanning the change is wrong.
    """

    __tablename__ = "symbol_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)


class PriceDaily(Base):
    """Raw unadjusted daily OHLCV. Primary key is (symbol_id, date).

    The composite primary key is what makes ingestion idempotent: re-running a
    date range updates existing rows instead of duplicating them.
    """

    __tablename__ = "price_daily"

    symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id", ondelete="CASCADE"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)

    open: Mapped[Decimal] = mapped_column(PRICE, nullable=False)
    high: Mapped[Decimal] = mapped_column(PRICE, nullable=False)
    low: Mapped[Decimal] = mapped_column(PRICE, nullable=False)
    close: Mapped[Decimal] = mapped_column(PRICE, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)

    source: Mapped[str] = mapped_column(String(30), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    symbol: Mapped[Symbol] = relationship(back_populates="bars")

    __table_args__ = (
        CheckConstraint("open > 0 AND high > 0 AND low > 0 AND close > 0",
                        name="ck_price_positive"),
        CheckConstraint("high >= low", name="ck_price_high_ge_low"),
        CheckConstraint("volume >= 0", name="ck_price_volume_non_negative"),
        Index("ix_price_daily_date", "date"),
    )

    def __repr__(self) -> str:
        return f"<PriceDaily symbol_id={self.symbol_id} {self.date} close={self.close}>"


class CorporateAction(Base):
    """Splits and dividends, stored separately so raw prices stay immutable."""

    __tablename__ = "corporate_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    action_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ratio: Mapped[Decimal | None] = mapped_column(RATIO)
    amount: Mapped[Decimal | None] = mapped_column(PRICE)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("symbol_id", "ex_date", "action_type", name="uq_corp_action"),
        CheckConstraint("action_type IN ('split','dividend')", name="ck_corp_action_type"),
    )


class IngestionRun(Base):
    """One row per ingestion job execution.

    This is what lets the dashboard say "data as of X" honestly, and what turns
    a silent failure into a visible one. A screen showing yesterday's numbers
    while looking current is the most dangerous UI failure mode there is.
    """

    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")

    range_start: Mapped[date | None] = mapped_column(Date)
    range_end: Mapped[date | None] = mapped_column(Date)

    symbols_requested: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    symbols_ok: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    symbols_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_written: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "status IN ('running','succeeded','failed','partial')",
            name="ck_ingestion_status",
        ),
    )


class DataQualityLog(Base):
    """Validation violations. Quarantined rows are recorded, never silently dropped."""

    __tablename__ = "data_quality_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="SET NULL"), index=True
    )
    symbol_id: Mapped[int | None] = mapped_column(
        ForeignKey("symbols.id", ondelete="CASCADE"), index=True
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[date | None] = mapped_column(Date)
    rule: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("severity IN ('error','warning')", name="ck_dq_severity"),
    )


class MetricsDaily(Base):
    """Precomputed derived metrics, one row per symbol per trading date.

    This table is what makes screening fast. Recomputing 200 days of moving
    averages across ~1,500 symbols at query time is slow and fragile; with the
    metrics already materialised, a screen becomes a single indexed SQL query.

    Recomputation is idempotent and re-runnable. Every column here is derived
    from price_daily and can be rebuilt from scratch at any time, so this table
    is a cache, never a source of truth.

    Columns are Float rather than Numeric on purpose. These are statistical
    quantities, not money -- nothing here determines a share count. Prices and
    P&L stay Numeric in price_daily.
    """

    __tablename__ = "metrics_daily"

    symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id", ondelete="CASCADE"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)

    # trend
    sma_20: Mapped[float | None] = mapped_column(Float)
    sma_50: Mapped[float | None] = mapped_column(Float)
    sma_200: Mapped[float | None] = mapped_column(Float)
    sma_200_rising: Mapped[bool | None] = mapped_column(Boolean)
    ma_aligned: Mapped[bool | None] = mapped_column(Boolean)

    # volatility
    atr_14: Mapped[float | None] = mapped_column(Float)
    atr_pct_14: Mapped[float | None] = mapped_column(Float)
    realized_vol_63: Mapped[float | None] = mapped_column(Float)

    # momentum
    ret_5: Mapped[float | None] = mapped_column(Float)
    ret_21: Mapped[float | None] = mapped_column(Float)
    ret_63: Mapped[float | None] = mapped_column(Float)
    ret_126: Mapped[float | None] = mapped_column(Float)
    ret_252: Mapped[float | None] = mapped_column(Float)

    # relative strength (vs benchmark, filled by a second pass)
    rs_63: Mapped[float | None] = mapped_column(Float)
    rs_adj_63: Mapped[float | None] = mapped_column(Float)

    # participation / structure
    rvol_20: Mapped[float | None] = mapped_column(Float)
    clv: Mapped[float | None] = mapped_column(Float)
    pct_from_252d_high: Mapped[float | None] = mapped_column(Float)

    # liquidity
    dollar_vol_50: Mapped[float | None] = mapped_column(Float)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_metrics_daily_date", "date"),)

    def __repr__(self) -> str:
        return f"<MetricsDaily symbol_id={self.symbol_id} {self.date}>"


class UniverseSnapshot(Base):
    """Point-in-time universe membership.

    Membership is stored per date rather than computed from today's data. A
    stock that failed the liquidity filter in 2019 was not tradeable in 2019,
    and screening history against today's universe is a textbook survivorship
    and look-ahead error.
    """

    __tablename__ = "universe_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False
    )
    definition_version: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        UniqueConstraint("name", "date", "symbol_id", name="uq_universe_member"),
    )
