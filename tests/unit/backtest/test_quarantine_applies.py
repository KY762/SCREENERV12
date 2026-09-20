"""The quarantine must apply at both doors into a backtest.

There are two: point-in-time membership, and the symbol loader. Most runs use
only the second -- `backtest run` and `research explore` default `--universe`
to None -- so filtering membership alone would leave BBBY's Overstock prices in
every battery while the quarantine reported success.

What breaks if these fail: a result computed from a series belonging to a
different company than the one that was in the index.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from screener.backtest.runner import load_symbol_bars
from screener.db.session import create_all
from screener.ingest.prices import _upsert_bars, get_or_create_symbol
from screener.universe import quarantine


def _bars(n=60):
    return pd.DataFrame(
        {
            "open": np.full(n, 100.0),
            "high": np.full(n, 101.0),
            "low": np.full(n, 99.0),
            "close": np.full(n, 100.0),
            "volume": np.full(n, 1_000_000.0),
        },
        index=pd.date_range("2013-01-02", periods=n, freq="B"),
    )


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    create_all(engine)
    with Session(engine) as s:
        sym = get_or_create_symbol(s, "BBBY", asset_type="equity")
        _upsert_bars(s, sym, _bars(), source="test")
        sym = get_or_create_symbol(s, "AAPL", asset_type="equity")
        _upsert_bars(s, sym, _bars(), source="test")
        yield s


@pytest.fixture
def contaminated(tmp_path, monkeypatch):
    """A quarantine naming BBBY, installed as the real one."""
    path = tmp_path / "q.csv"
    quarantine.write(
        [
            quarantine.Excluded(
                symbol="BBBY", reason="outlived_its_security",
                holder="Bed Bath & Beyond, Inc.", recorded_on=date(2026, 9, 19),
                detail="the 2013-2015 closes are Overstock's",
            )
        ],
        path,
    )
    quarantine.symbols.cache_clear()
    monkeypatch.setattr(quarantine, "QUARANTINE_FILE", path)
    yield path
    quarantine.symbols.cache_clear()


def test_a_quarantined_symbol_is_not_loaded(session, contaminated):
    """The default path: no --universe, so membership is never consulted and
    this is the only filter standing between a contaminated series and a
    published number."""
    assert "BBBY" not in load_symbol_bars(session, None)
    assert "AAPL" in load_symbol_bars(session, None)


def test_naming_a_quarantined_symbol_explicitly_does_not_load_it(session, contaminated):
    """A contaminated series is not more trustworthy for having been asked for
    by name."""
    loaded = load_symbol_bars(session, "BBBY,AAPL")

    assert set(loaded) == {"AAPL"}


def test_the_exclusion_is_announced(session, contaminated, caplog):
    """An exclusion nobody can see is worse than the contamination it removes:
    a run that silently drops a symbol looks identical to one where the symbol
    was never ingested."""
    with caplog.at_level("WARNING"):
        load_symbol_bars(session, None)

    assert "BBBY" in caplog.text
    assert "quarantine" in caplog.text


def test_nothing_is_dropped_when_the_quarantine_is_empty(session, tmp_path, monkeypatch):
    """The filter must not become a way to lose symbols by accident."""
    quarantine.symbols.cache_clear()
    monkeypatch.setattr(quarantine, "QUARANTINE_FILE", tmp_path / "absent.csv")

    assert set(load_symbol_bars(session, None)) == {"AAPL", "BBBY"}

    quarantine.symbols.cache_clear()
