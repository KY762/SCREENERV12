from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from screener.db.session import create_all
from screener.providers.base import BarRequest, CorporateAction, ProviderError


class FakeProvider:
    """In-memory PriceProvider. Lets ingestion be tested end to end with no
    network, no credentials, and fully deterministic data."""

    name = "fake"

    def __init__(self, frames: dict[str, pd.DataFrame] | None = None, raises: str | None = None):
        self.frames = frames or {}
        self.raises = raises
        self.calls: list[BarRequest] = []

    def get_daily_bars(self, request: BarRequest) -> pd.DataFrame:
        self.calls.append(request)
        if self.raises:
            raise ProviderError(self.raises)
        parts = []
        for sym in request.symbols:
            df = self.frames.get(sym)
            if df is None or df.empty:
                continue
            part = df.copy()
            part["symbol"] = sym
            part["date"] = [d.date() if hasattr(d, "date") else d for d in part.index]
            parts.append(part.reset_index(drop=True))
        if not parts:
            idx = pd.MultiIndex.from_arrays([[], []], names=["symbol", "date"])
            return pd.DataFrame(
                {c: pd.Series(dtype="float64")
                 for c in ("open", "high", "low", "close", "volume")},
                index=idx,
            )
        out = pd.concat(parts, ignore_index=True)
        cols = ["symbol", "date", "open", "high", "low", "close", "volume"]
        return out[cols].set_index(["symbol", "date"]).sort_index()

    def get_corporate_actions(self, symbols, start, end) -> list[CorporateAction]:
        return []


def make_bars(rows, start="2024-01-02") -> pd.DataFrame:
    return pd.DataFrame(
        rows, columns=["open", "high", "low", "close", "volume"],
        index=pd.date_range(start, periods=len(rows), freq="B"),
    ).astype(float)


CLEAN_ROWS = [
    [100, 105, 98, 103, 1_000_000],
    [103, 108, 102, 107, 1_200_000],
    [107, 110, 104, 105, 900_000],
    [105, 112, 103, 111, 1_500_000],
]


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://")
    create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def clean_provider() -> FakeProvider:
    return FakeProvider({"SPY": make_bars(CLEAN_ROWS)})


@pytest.fixture
def window() -> tuple[date, date]:
    return date(2024, 1, 1), date(2024, 1, 31)
