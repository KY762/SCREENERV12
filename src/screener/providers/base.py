"""Provider abstraction.

Every external data source sits behind one of these Protocols. Swapping Alpaca
for Polygon means writing one new adapter class and changing a config value --
nothing else in the codebase imports a vendor SDK directly.

That boundary is the reason the assessment could recommend starting on free data
without committing to it: the migration cost is bounded and known in advance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable

import pandas as pd


@dataclass(frozen=True)
class BarRequest:
    symbols: tuple[str, ...]
    start: date
    end: date
    adjustment: str = "raw"  # see PriceProvider.get_daily_bars


@dataclass(frozen=True)
class CorporateAction:
    symbol: str
    ex_date: date
    action_type: str  # "split" | "dividend"
    ratio: float | None = None
    amount: float | None = None


class ProviderError(RuntimeError):
    """Raised when a provider fails in a way the caller must handle.

    Deliberately distinct from a bare exception: ingestion catches this, records
    the failure in ingestion_runs, and continues with other symbols rather than
    aborting a nightly job because one ticker misbehaved.
    """


@runtime_checkable
class PriceProvider(Protocol):
    """Daily OHLCV and corporate actions.

    IMPORTANT -- adjustment policy. The platform stores RAW, UNADJUSTED bars plus
    a separate corporate-actions table, and derives adjusted series on demand.
    Storing pre-adjusted prices makes history mutate under you: a split today
    silently rewrites what you believed in 2019, which is a direct route to
    look-ahead bias in backtests. Adapters must default to ``adjustment="raw"``.
    """

    name: str

    def get_daily_bars(self, request: BarRequest) -> pd.DataFrame:
        """Return tidy bars indexed by (symbol, date).

        Columns: open, high, low, close, volume. Empty frame if no data.
        Raises ProviderError on an unrecoverable failure.
        """
        ...

    def get_corporate_actions(
        self, symbols: tuple[str, ...], start: date, end: date
    ) -> list[CorporateAction]:
        ...


@runtime_checkable
class FundamentalsProvider(Protocol):
    """Point-in-time fundamentals.

    Implementations must record the FILING date, not just the fiscal period.
    A restated figure is not what was knowable at the time, and treating it as
    such is look-ahead bias wearing a respectable suit.
    """

    name: str

    def get_fundamentals(self, symbol: str) -> pd.DataFrame: ...


@runtime_checkable
class EventsProvider(Protocol):
    """Scheduled events: earnings dates, economic releases, Fed meetings."""

    name: str

    def get_events(self, start: date, end: date, symbols: tuple[str, ...] | None = None): ...


@runtime_checkable
class NewsProvider(Protocol):
    name: str

    def get_news(self, symbols: tuple[str, ...], start: date, end: date): ...
