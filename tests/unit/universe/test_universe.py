"""Universe tests.

The property that matters most is point-in-time correctness. A universe built
from today's data quietly selects the companies that went on to become large and
liquid, which inflates every backtest run against it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from screener.db.models import UniverseSnapshot
from screener.db.session import create_all
from screener.ingest.prices import _upsert_bars, get_or_create_symbol
from screener.metrics.compute import build_metrics
from screener.universe.build import build_universe, eligible_frame, universe_members
from screener.universe.definition import (
    UniverseDefinition,
    is_leveraged_or_inverse,
    passes_static_filters,
)

# --- static filters --------------------------------------------------------

@pytest.mark.parametrize("ticker", ["TQQQ", "SQQQ", "SOXL", "UVXY", "tqqq"])
def test_known_leveraged_tickers_are_excluded(ticker):
    assert is_leveraged_or_inverse(ticker)


@pytest.mark.parametrize(
    "name",
    [
        "ProShares UltraPro QQQ",
        "Direxion Daily Semiconductor Bull 3X Shares",
        "ProShares Short S&P500 Inverse",
        "Some 2x Leveraged Fund",
    ],
)
def test_leveraged_names_are_excluded(name):
    assert is_leveraged_or_inverse("XXXX", name)


@pytest.mark.parametrize(
    "ticker,name",
    [
        ("SPY", "SPDR S&P 500 ETF Trust"),
        ("AAPL", "Apple Inc."),
        ("XLF", "Financial Select Sector SPDR"),
        # "Ulta" is not "Ultra". The pattern matches an 'ultra' prefix because
        # ProShares runs the words together ("UltraPro"), and this is the
        # obvious false positive that change could have introduced.
        ("ULTA", "Ulta Beauty Inc."),
    ],
)
def test_ordinary_instruments_are_not_flagged(ticker, name):
    assert not is_leveraged_or_inverse(ticker, name)


@pytest.mark.parametrize(
    "name",
    ["ProShares UltraPro QQQ", "ProShares UltraShort S&P500"],
)
def test_run_together_issuer_names_are_caught(name):
    """Regression: a word-boundary-terminated 'ultra' pattern silently missed
    every ProShares Ultra* product."""
    assert is_leveraged_or_inverse("XXXX", name)


def test_restricted_list_blocks_a_symbol():
    """The employer-compliance hook. Empty by default, binding when populated."""
    definition = UniverseDefinition(restricted_tickers=frozenset({"BAC"}))
    ok, reason = passes_static_filters(definition, ticker="BAC", asset_type="equity")
    assert not ok and reason == "restricted list"


def test_disallowed_asset_type_is_excluded():
    definition = UniverseDefinition()
    ok, reason = passes_static_filters(definition, ticker="XYZ", asset_type="fund")
    assert not ok and "not eligible" in reason


def test_leveraged_exclusion_can_be_switched_off():
    definition = UniverseDefinition(exclude_leveraged=False)
    ok, _ = passes_static_filters(definition, ticker="TQQQ", asset_type="etf")
    assert ok


# --- date-varying eligibility ----------------------------------------------

def _metrics(dollar_vols) -> pd.DataFrame:
    return pd.DataFrame(
        {"dollar_vol_50": dollar_vols},
        index=pd.date_range("2024-01-02", periods=len(dollar_vols), freq="B"),
    )


def test_eligibility_requires_price_liquidity_and_history():
    definition = UniverseDefinition(min_history_days=3)
    metrics = _metrics([50e6, 50e6, 50e6, 50e6, 50e6])
    closes = pd.Series([20.0] * 5, index=metrics.index)

    mask = eligible_frame(metrics, closes, definition)
    assert list(mask) == [False, False, True, True, True], "history requirement"


def test_a_symbol_below_the_price_floor_is_ineligible_on_that_date():
    definition = UniverseDefinition(min_history_days=1)
    metrics = _metrics([50e6, 50e6, 50e6])
    closes = pd.Series([20.0, 9.99, 20.0], index=metrics.index)

    assert list(eligible_frame(metrics, closes, definition)) == [True, False, True]


def test_illiquid_dates_are_ineligible():
    definition = UniverseDefinition(min_history_days=1)
    metrics = _metrics([50e6, 1e6, 50e6])
    closes = pd.Series([20.0] * 3, index=metrics.index)

    assert list(eligible_frame(metrics, closes, definition)) == [True, False, True]


def test_nan_dollar_volume_is_ineligible_not_eligible():
    """NaN means the 50-day window is not yet full, which is itself a failure of
    the history requirement. Treating it as a pass would admit symbols on their
    first day of trading."""
    definition = UniverseDefinition(min_history_days=1)
    metrics = _metrics([np.nan, np.nan, 50e6])
    closes = pd.Series([20.0] * 3, index=metrics.index)

    assert list(eligible_frame(metrics, closes, definition)) == [False, False, True]


# --- persistence -----------------------------------------------------------

def _synthetic(n=320, price=50.0, volume=2_000_000, seed=3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = price * np.exp(np.cumsum(rng.normal(0.0004, 0.012, n)))
    spread = np.abs(rng.normal(0.01, 0.003, n)) * close
    o = close * (1 + rng.normal(0, 0.003, n))
    return pd.DataFrame(
        {
            "open": o,
            "high": np.maximum(o, close) + spread * 0.5,
            "low": np.minimum(o, close) - spread * 0.5,
            "close": close,
            "volume": np.full(n, float(volume)),
        },
        index=pd.date_range("2023-01-02", periods=n, freq="B"),
    )


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://")
    create_all(engine)
    with Session(engine) as s:
        yield s


def _seed(session, ticker, bars, asset_type="equity", name=None):
    sym = get_or_create_symbol(session, ticker, asset_type=asset_type, name=name)
    _upsert_bars(session, sym, bars, source="test")
    return sym


def test_build_universe_persists_point_in_time_membership(session):
    _seed(session, "SPY", _synthetic())
    build_metrics(session, ["SPY"])

    result = build_universe(session, UniverseDefinition(min_history_days=250))
    assert result.memberships_written > 0
    assert session.scalar(select(UniverseSnapshot.name)) == "liquid_us"


def test_membership_is_absent_before_the_history_requirement_is_met(session):
    """The point of the whole module: a symbol is not in the universe on a date
    when it did not yet qualify."""
    bars = _synthetic(320)
    _seed(session, "SPY", bars)
    build_metrics(session, ["SPY"])
    build_universe(session, UniverseDefinition(min_history_days=250))

    early = bars.index[10].date()
    late = bars.index[-1].date()

    assert universe_members(session, "liquid_us", early) == []
    assert universe_members(session, "liquid_us", late) == ["SPY"]


def test_illiquid_symbol_never_joins(session):
    """$50 x 1,000 shares = $50k/day, far below the $20M floor."""
    _seed(session, "TINY", _synthetic(volume=1_000))
    build_metrics(session, ["TINY"])
    result = build_universe(session, UniverseDefinition(min_history_days=250))

    assert result.memberships_written == 0


def test_leveraged_etf_is_excluded_before_any_date_evaluation(session):
    _seed(session, "TQQQ", _synthetic(), asset_type="etf")
    build_metrics(session, ["TQQQ"])
    result = build_universe(session)

    assert "TQQQ" in result.symbols_excluded_static
    assert result.symbols_excluded_static["TQQQ"] == "leveraged or inverse product"
    assert result.memberships_written == 0


def test_build_is_idempotent(session):
    _seed(session, "SPY", _synthetic())
    build_metrics(session, ["SPY"])
    definition = UniverseDefinition(min_history_days=250)

    first = build_universe(session, definition)
    second = build_universe(session, definition)

    assert first.memberships_written > 0
    assert second.memberships_written == 0, "re-running must not duplicate membership"


def test_definition_version_is_recorded_with_every_row(session):
    """A change to any threshold is a change of definition, not a tweak. Storing
    the version is what makes an old snapshot interpretable later."""
    _seed(session, "SPY", _synthetic())
    build_metrics(session, ["SPY"])
    build_universe(session, UniverseDefinition(version="v1", min_history_days=250))

    row = session.scalars(select(UniverseSnapshot).limit(1)).one()
    assert row.definition_version == "v1"


def test_capacity_floor_is_derived_from_position_size_not_convention():
    """The $20M floor in liquid_us is an institutional convention. At $10,000
    with a 25% cap, the largest order is $2,500, and 1% participation implies
    a $250k floor -- two orders of magnitude lower. Hard-coding $20M excludes
    the small companies the pool was widened to reach."""
    from screener.universe.definition import capacity_floor

    assert capacity_floor(10_000.0) == pytest.approx(250_000.0)


def test_capacity_floor_scales_with_equity():
    """The same rule that admits a $250k-a-day stock at $10,000 must exclude it
    at $1,000,000 without anyone editing a threshold. At institutional size it
    reproduces the institutional number, which is the sanity check."""
    from screener.universe.definition import capacity_floor

    assert capacity_floor(50_000.0) == pytest.approx(1_250_000.0)
    assert capacity_floor(1_000_000.0) == pytest.approx(25_000_000.0)


def test_capacity_floor_rejects_impossible_inputs():
    """A zero participation ceiling implies an infinite floor. Returning inf
    would silently empty the universe instead of failing loudly."""
    from screener.universe.definition import capacity_floor

    for kwargs in (
        {"equity": 0.0},
        {"equity": 10_000.0, "max_position_pct": 0.0},
        {"equity": 10_000.0, "max_participation_pct": 0.0},
    ):
        equity = kwargs.pop("equity")
        with pytest.raises(ValueError):
            capacity_floor(equity, **kwargs)


def test_reachable_us_does_not_mutate_the_pre_registered_definition():
    """liquid_us is pre-registered in docs/03 section 0.1. A second question
    gets a second named definition; retuning the first would make every earlier
    result incomparable and unreproducible."""
    from screener.universe.definition import REACHABLE_US, UniverseDefinition

    liquid = UniverseDefinition()

    assert liquid.name == "liquid_us"
    assert liquid.min_dollar_volume == pytest.approx(20_000_000.0)
    assert liquid.min_price == pytest.approx(10.00)

    assert REACHABLE_US.name == "reachable_us"
    assert REACHABLE_US.min_dollar_volume == pytest.approx(250_000.0)
    assert REACHABLE_US.min_price == pytest.approx(5.00)
    assert REACHABLE_US.describe() != liquid.describe()
