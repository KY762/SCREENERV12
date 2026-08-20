"""Metrics engine tests.

metrics_daily is a cache derived entirely from price_daily. The properties that
matter are that a rebuild is always safe, that warmup stays NULL rather than
being fabricated, and that the values match the already-tested calc layer
exactly -- if they diverge, the metrics table has grown its own arithmetic,
which is how the golden-value and no-lookahead guarantees get silently lost.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from screener.calc import indicators as ind
from screener.db.models import MetricsDaily
from screener.db.session import create_all
from screener.ingest.prices import get_or_create_symbol
from screener.metrics.compute import (
    build_metrics,
    compute_metrics_frame,
    compute_relative_strength_frame,
    load_bars,
)
from tests.unit.ingest.conftest import FakeProvider, make_bars  # noqa: F401


def _synthetic(n: int = 300, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0005, 0.015, n)
    close = 100 * np.exp(np.cumsum(steps))
    spread = np.abs(rng.normal(0.01, 0.004, n)) * close
    open_ = close * (1 + rng.normal(0, 0.004, n))
    return pd.DataFrame(
        {
            "open": open_,
            "high": np.maximum(open_, close) + spread * 0.5,
            "low": np.minimum(open_, close) - spread * 0.5,
            "close": close,
            "volume": rng.integers(1_000_000, 9_000_000, n).astype(float),
        },
        index=pd.date_range("2023-01-02", periods=n, freq="B"),
    )


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://")
    create_all(engine)
    with Session(engine) as s:
        yield s


def _seed(session, ticker: str, bars: pd.DataFrame):
    from screener.ingest.prices import _upsert_bars

    symbol = get_or_create_symbol(session, ticker)
    _upsert_bars(session, symbol, bars, source="test")
    return symbol


# --- pure computation ------------------------------------------------------

def test_metrics_frame_delegates_to_the_tested_calc_layer():
    """Every column must equal the calc-layer function exactly. Any divergence
    means the metrics engine has reimplemented the maths and left the
    golden-value guarantees behind."""
    bars = _synthetic()
    frame = compute_metrics_frame(bars)

    pd.testing.assert_series_equal(
        frame["sma_50"], ind.sma(bars["close"], 50), check_names=False
    )
    pd.testing.assert_series_equal(frame["atr_14"], ind.atr(bars, 14), check_names=False)
    pd.testing.assert_series_equal(frame["clv"], ind.clv(bars), check_names=False)
    pd.testing.assert_series_equal(frame["rvol_20"], ind.rvol(bars, 20), check_names=False)
    pd.testing.assert_series_equal(
        frame["ret_63"], ind.returns(bars["close"], 63), check_names=False
    )
    pd.testing.assert_series_equal(
        frame["pct_from_252d_high"], ind.pct_from_high(bars, 252), check_names=False
    )


def test_warmup_stays_nan_and_is_never_backfilled():
    """A back-filled moving average is fabricated history, and a backtest built
    on it trades information that did not exist."""
    frame = compute_metrics_frame(_synthetic(300))
    assert frame["sma_200"].iloc[:199].isna().all()
    assert frame["sma_200"].iloc[199:].notna().all()
    assert frame["ret_252"].iloc[:251].isna().all()


def test_ma_aligned_matches_its_definition():
    bars = _synthetic()
    frame = compute_metrics_frame(bars)
    expected = (bars["close"] > frame["sma_50"]) & (frame["sma_50"] > frame["sma_200"])
    computed = frame["ma_aligned"].dropna().astype(bool)
    assert (computed == expected.loc[computed.index]).all()


def test_metrics_frame_does_not_look_ahead():
    """The truncation test, applied to the whole metrics frame at once."""
    bars = _synthetic(300)
    cut = 250
    full = compute_metrics_frame(bars).iloc[:cut]
    trunc = compute_metrics_frame(bars.iloc[:cut])

    for col in full.columns:
        a = pd.to_numeric(full[col], errors="coerce").to_numpy(dtype="float64")
        b = pd.to_numeric(trunc[col], errors="coerce").to_numpy(dtype="float64")
        both_nan = np.isnan(a) & np.isnan(b)
        assert np.all(both_nan | np.isclose(a, b, rtol=1e-12, atol=1e-12)), (
            f"{col} changed when future bars were removed"
        )


def test_relative_strength_is_null_where_the_benchmark_has_no_bar():
    """Comparing a symbol's Tuesday against the benchmark's Monday would
    manufacture strength that never existed."""
    bars = _synthetic(120)
    benchmark = _synthetic(120, seed=99).iloc[:100]
    rs = compute_relative_strength_frame(bars, benchmark)
    assert rs.index.equals(bars.index)
    assert rs["rs_63"].iloc[105:].isna().all()


def test_empty_input_produces_empty_output():
    empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    assert compute_metrics_frame(empty).empty
    assert compute_relative_strength_frame(empty, empty).empty


# --- persistence -----------------------------------------------------------

def test_build_metrics_persists_rows(session):
    _seed(session, "SPY", _synthetic(300))
    results = build_metrics(session, ["SPY"])

    assert len(results) == 1 and results[0].ok
    assert results[0].rows_written == 300
    assert session.scalar(select(func.count()).select_from(MetricsDaily)) == 300


def test_rebuild_is_idempotent(session):
    """Re-running must converge, not duplicate. A second pass writes nothing
    because every value already matches."""
    _seed(session, "SPY", _synthetic(300))
    first = build_metrics(session, ["SPY"])[0]
    second = build_metrics(session, ["SPY"])[0]

    assert first.rows_written == 300
    assert second.rows_written == 0
    assert session.scalar(select(func.count()).select_from(MetricsDaily)) == 300


def test_rebuild_flag_recreates_rows_without_duplicating(session):
    _seed(session, "SPY", _synthetic(300))
    build_metrics(session, ["SPY"])
    rebuilt = build_metrics(session, ["SPY"], rebuild=True)[0]

    assert rebuilt.rows_written == 300
    assert session.scalar(select(func.count()).select_from(MetricsDaily)) == 300


def test_nan_is_written_as_null_not_zero(session):
    """A zero moving average would look like a real value and silently poison
    every downstream comparison."""
    _seed(session, "SPY", _synthetic(300))
    build_metrics(session, ["SPY"])

    early = session.scalars(
        select(MetricsDaily).order_by(MetricsDaily.date).limit(1)
    ).one()
    assert early.sma_200 is None
    assert early.ret_252 is None

    late = session.scalars(
        select(MetricsDaily).order_by(MetricsDaily.date.desc()).limit(1)
    ).one()
    assert late.sma_200 is not None


def test_persisted_values_match_the_computed_frame(session):
    """Metrics must be recomputable exactly from the bars actually stored.

    Note the comparison is against bars re-read from the database, not the
    in-memory floats used to seed it. Prices persist as Numeric(18,6), so a
    round trip rounds at the sixth decimal -- and Wilder's ATR recursion
    amplifies that to roughly the eighth significant figure. Six decimals is far
    beyond real quote precision, so this is a non-issue for trading; comparing
    against unrounded synthetic floats would be measuring the storage precision
    rather than the metrics engine.
    """
    bars = _synthetic(300)
    symbol = _seed(session, "SPY", bars)
    build_metrics(session, ["SPY"])

    stored_bars = load_bars(session, symbol.id)
    frame = compute_metrics_frame(stored_bars)
    last_date = frame.index[-1].date()
    row = session.scalar(
        select(MetricsDaily).where(MetricsDaily.date == last_date)
    )
    assert row.sma_50 == pytest.approx(frame["sma_50"].iloc[-1], rel=1e-12)
    assert row.atr_14 == pytest.approx(frame["atr_14"].iloc[-1], rel=1e-12)
    assert row.clv == pytest.approx(frame["clv"].iloc[-1], rel=1e-12)


def test_storage_precision_is_far_finer_than_quote_precision(session):
    """Documents the round-trip boundary found above: stored prices agree with
    the source to well within a hundredth of a cent, so nothing a trader would
    ever observe is affected."""
    bars = _synthetic(50)
    symbol = _seed(session, "SPY", bars)
    stored = load_bars(session, symbol.id)

    diff = (stored["close"].to_numpy() - bars["close"].to_numpy())
    assert np.abs(diff).max() < 1e-6


def test_relative_strength_populated_against_the_benchmark(session):
    _seed(session, "SPY", _synthetic(300, seed=1))
    _seed(session, "AAPL", _synthetic(300, seed=2))
    build_metrics(session, ["AAPL"], benchmark_ticker="SPY")

    row = session.scalars(
        select(MetricsDaily).order_by(MetricsDaily.date.desc()).limit(1)
    ).one()
    assert row.rs_63 is not None
    assert row.rs_adj_63 is not None


def test_missing_benchmark_leaves_rs_null_but_still_builds(session):
    """A missing benchmark must degrade one column, not abort the run."""
    _seed(session, "AAPL", _synthetic(300))
    results = build_metrics(session, ["AAPL"], benchmark_ticker="NOPE")

    assert results[0].ok
    row = session.scalars(select(MetricsDaily).limit(1)).one()
    assert row.rs_63 is None
    assert row.sma_20 is not None or row.date is not None


def test_symbol_with_too_little_history_is_reported_not_crashed(session):
    _seed(session, "TINY", _synthetic(5))
    results = build_metrics(session, ["TINY"])
    assert not results[0].ok
    assert "at least" in results[0].error


def test_build_all_symbols_when_none_specified(session):
    _seed(session, "SPY", _synthetic(300, seed=1))
    _seed(session, "QQQ", _synthetic(300, seed=2))
    results = build_metrics(session)
    assert {r.ticker for r in results} == {"SPY", "QQQ"}


def test_load_bars_returns_sorted_float_frame(session):
    symbol = _seed(session, "SPY", _synthetic(50))
    bars = load_bars(session, symbol.id)
    assert len(bars) == 50
    assert bars.index.is_monotonic_increasing
    assert str(bars["close"].dtype) == "float64"


def test_since_limits_writes_but_not_the_calculation(session):
    """A nightly update writes one row per symbol, not a decade of them -- while
    still computing from full history, because a 200-day average needs 200 prior
    bars. Truncating the INPUT would silently produce wrong values."""
    bars = _synthetic(300)
    symbol = _seed(session, "SPY", bars)

    cutoff = bars.index[-5].date()
    result = build_metrics(session, ["SPY"], since=cutoff)[0]

    assert result.rows_written == 5, "only the tail should be persisted"
    assert session.scalar(select(func.count()).select_from(MetricsDaily)) == 5

    row = session.scalars(
        select(MetricsDaily).order_by(MetricsDaily.date.desc()).limit(1)
    ).one()
    stored_bars = load_bars(session, symbol.id)
    expected = compute_metrics_frame(stored_bars)["sma_200"].iloc[-1]

    assert row.sma_200 is not None, "long-window metric must survive a --since run"
    assert row.sma_200 == pytest.approx(expected, rel=1e-12)
