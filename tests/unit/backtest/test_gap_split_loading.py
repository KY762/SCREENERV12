"""A ticker that changed hands loads as two series, not one.

What breaks if these fail: the backtest's only door for bars hands the engine
Sun Microsystems and a 2021 ETF as one stock, and membership or earnings dated
to one holder are attributed to the other.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from screener.backtest.runner import load_symbol_bars
from screener.calc.segments import MAX_GAP_DAYS
from screener.db.session import create_all
from screener.ingest.prices import _upsert_bars, get_or_create_symbol
from screener.universe import quarantine


def _bars(index, price):
    n = len(index)
    return pd.DataFrame(
        {"open": np.full(n, price), "high": np.full(n, price),
         "low": np.full(n, price), "close": np.full(n, price),
         "volume": np.full(n, 1_000_000.0)},
        index=index,
    )


OLD = pd.bdate_range("2009-01-02", periods=60)
NEW = pd.bdate_range(OLD[-1] + pd.Timedelta(days=MAX_GAP_DAYS + 300), periods=60)


@pytest.fixture
def session(tmp_path, monkeypatch):
    quarantine.symbols.cache_clear()
    monkeypatch.setattr(quarantine, "QUARANTINE_FILE", tmp_path / "absent.csv")
    engine = create_engine("sqlite://")
    create_all(engine)
    with Session(engine) as s:
        sym = get_or_create_symbol(s, "JAVA", asset_type="equity")
        _upsert_bars(s, sym, pd.concat([_bars(OLD, 5.0), _bars(NEW, 60.0)]), source="test")
        sym = get_or_create_symbol(s, "AAPL", asset_type="equity")
        _upsert_bars(s, sym, _bars(pd.bdate_range("2009-01-02", periods=300), 20.0),
                     source="test")
        yield s
    quarantine.symbols.cache_clear()


def test_a_reused_ticker_loads_as_two_series(session):
    loaded = load_symbol_bars(session, None)

    old_key = f"JAVA@{OLD[-1]:%Y-%m-%d}"
    assert set(loaded) == {"AAPL", "JAVA", old_key}
    assert (loaded[old_key]["close"] == 5.0).all()
    assert (loaded["JAVA"]["close"] == 60.0).all()


def test_an_unbroken_ticker_is_unaffected(session):
    loaded = load_symbol_bars(session, None)

    assert len(loaded["AAPL"]) == 300


def test_naming_the_ticker_loads_both_of_its_series(session):
    """Asking for JAVA by name asks for the letters, and both holders had them."""
    assert len([k for k in load_symbol_bars(session, "JAVA") if k.startswith("JAVA")]) == 2


def test_membership_applies_to_whichever_series_was_trading(monkeypatch):
    from screener.backtest import runner

    monkeypatch.setattr(
        "screener.universe.build.universe_members",
        lambda session, name, day: ["JAVA"],
    )
    predicate = runner.universe_filter(object(), "sp500_pit")

    assert predicate(f"JAVA@{OLD[-1]:%Y-%m-%d}", OLD[5].date())
    assert predicate("JAVA", NEW[5].date())
    assert not predicate("AAPL", OLD[5].date())
