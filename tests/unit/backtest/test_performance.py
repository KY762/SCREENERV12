"""Statistics with hand-computed expected values."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from screener.backtest.engine import BacktestResult, Trade
from screener.backtest.performance import (
    RegimeResult,
    all_passed,
    by_regime,
    check_criteria,
    max_drawdown,
    summarize,
)


def trade(pnl_per_share: float, risk: float = 100.0, entry_day: str = "2013-03-01") -> Trade:
    """One closed trade with a chosen P&L. Shares fixed at 1 for clarity."""
    entry = Decimal("100.00")
    return Trade(
        ticker="AAA",
        setup="test",
        entry_date=date.fromisoformat(entry_day),
        entry_price=entry,
        shares=1,
        stop=Decimal("95.00"),
        target=None,
        risk_dollars=Decimal(str(risk)),
        exit_date=date.fromisoformat(entry_day),
        exit_price=entry + Decimal(str(pnl_per_share)),
        exit_reason="target" if pnl_per_share > 0 else "stop",
        bars_held=4,
    )


def result_of(trades: list[Trade], curve: list[float] | None = None) -> BacktestResult:
    series = pd.Series(
        curve or [10_000.0, 10_000.0],
        index=pd.bdate_range("2013-03-01", periods=len(curve or [0, 0])),
    )
    return BacktestResult(
        trades=trades,
        equity_curve=series,
        starting_equity=Decimal("10000.00"),
        ending_equity=Decimal(str(series.iloc[-1])),
    )


def test_expectancy_and_profit_factor_by_hand():
    # Three winners at +200, two losers at -100. Risk is 100 per trade.
    # Gross profit 600, gross loss 200 -> PF 3.0
    # Total P&L 400 over 5 trades -> mean 80 dollars = +0.8R
    trades = [trade(200), trade(200), trade(200), trade(-100), trade(-100)]
    stats = summarize(result_of(trades))

    assert stats.trades == 5
    assert stats.wins == 3
    assert stats.win_rate == pytest.approx(0.6)
    assert stats.gross_profit == pytest.approx(600.0)
    assert stats.gross_loss == pytest.approx(200.0)
    assert stats.profit_factor == pytest.approx(3.0)
    assert stats.expectancy_r == pytest.approx(0.8)
    assert stats.expectancy_dollars == pytest.approx(80.0)


def test_profit_factor_is_infinite_when_nothing_lost():
    """Reported, not hidden -- an infinite PF means too few trades, and the
    trade-count criterion is what catches it."""
    stats = summarize(result_of([trade(50), trade(75)]))
    assert stats.profit_factor == float("inf")


def test_max_drawdown_by_hand():
    # 100 -> 120 -> 90: peak 120, trough 90, drawdown 25%
    curve = pd.Series([100.0, 120.0, 90.0, 110.0])
    assert max_drawdown(curve) == pytest.approx(0.25)


def test_max_drawdown_of_a_rising_curve_is_zero():
    assert max_drawdown(pd.Series([100.0, 101.0, 102.0])) == pytest.approx(0.0)


def test_regime_buckets_report_none_rather_than_zero_when_empty():
    """'No trades in this regime' and 'no edge in this regime' are different
    findings and must not collapse into the same number."""
    buckets = by_regime([trade(100, entry_day="2013-03-01")])
    assert buckets["bull_2013_2014"].trades == 1
    assert "crash_2020" not in buckets


def regimes_of(trades, equity=10_000, percentile=None):
    """RegimeResults from bucket stats, with an optional same-day rank."""
    return {
        name: RegimeResult(name, s.trades, s.total_return_pct, percentile)
        for name, s in by_regime(trades, equity).items()
    }


def test_criteria_fail_on_trade_count_even_when_everything_else_is_good():
    """The floor counts EFFECTIVE observations since 2026-09-19, so three
    trades fail it just as three did before."""
    trades = [trade(200), trade(200), trade(-100)]
    stats = summarize(result_of(trades))
    results = check_criteria(
        stats, effective_trades=3.0, regimes=regimes_of(trades),
        regime_buckets_in_split=3, same_day_p=0.01,
    )

    by_name = {r.name: r for r in results}
    assert by_name["expectancy"].passed
    assert by_name["profit_factor"].passed
    assert not by_name["trade_count"].passed
    assert not all_passed(results)


def test_missing_random_benchmark_counts_as_a_failure_not_a_skip():
    """A criterion that was never measured has not been met."""
    stats = summarize(result_of([trade(100)]))
    results = check_criteria(
        stats, effective_trades=500.0, regimes={},
        regime_buckets_in_split=3, same_day_p=None,
    )
    vs_random = next(r for r in results if r.name == "vs_random")
    assert not vs_random.passed
    assert vs_random.observed == "not run"


# --------------------------------------------------------------------------
# Regime units -- the live run printed "worst -19725.7%"
# --------------------------------------------------------------------------

def test_regime_return_is_a_return_not_a_sum_of_r_multiples():
    """A bucket holding a sum of R was compared against a -15% floor and
    formatted as a percentage, so -197 R displayed as -19725.7%. The unit has
    to match the threshold it is tested against."""
    # Two trades, one share each, -100 dollars total, on 10,000 of equity.
    trades = [trade(-50), trade(-50)]

    buckets = by_regime(trades, starting_equity=10_000)

    assert buckets["bull_2013_2014"].total_return_pct == pytest.approx(-0.01)


def test_regime_return_scales_with_account_size():
    trades = [trade(-50), trade(-50)]

    small = by_regime(trades, starting_equity=1_000)["bull_2013_2014"]
    large = by_regime(trades, starting_equity=100_000)["bull_2013_2014"]

    assert small.total_return_pct == pytest.approx(-0.10)
    assert large.total_return_pct == pytest.approx(-0.001)


def test_robustness_criterion_reads_the_corrected_unit():
    """A -1% regime must not fail a -15% floor."""
    trades = [trade(-50), trade(-50)]
    stats = summarize(result_of(trades))

    results = check_criteria(
        stats, effective_trades=500.0, regimes=regimes_of(trades, 10_000, percentile=90.0),
        regime_buckets_in_split=3, same_day_p=0.01,
    )
    robustness = next(r for r in results if r.name == "regime_robustness")

    assert "-1.0%" in robustness.observed


# --------------------------------------------------------------------------
# The 2026-09-19 amendment
#
# Every criterion now asks whether the rule PICKS well, rather than a mix of
# picking, market direction and timing.
# --------------------------------------------------------------------------

def test_the_trade_floor_counts_independent_observations():
    """566 raw trades holding 385 independent ones passes; the same raw count
    holding 150 does not. Concurrent positions in correlated names are not
    separate evidence (backtest/inference.py)."""
    stats = summarize(result_of([trade(100)] * 3))
    common = dict(regimes=regimes_of([trade(100)], percentile=90.0),
                  regime_buckets_in_split=3, same_day_p=0.001)

    enough = check_criteria(stats, effective_trades=385.0, **common)
    thin = check_criteria(stats, effective_trades=150.0, **common)

    assert next(r for r in enough if r.name == "trade_count").passed
    assert not next(r for r in thin if r.name == "trade_count").passed


def test_an_unestimable_design_effect_fails_rather_than_passes():
    stats = summarize(result_of([trade(100)]))
    results = check_criteria(
        stats, effective_trades=None, regimes={}, regime_buckets_in_split=3,
        same_day_p=0.001,
    )
    assert not next(r for r in results if r.name == "trade_count").passed


def test_regimes_ask_whether_the_picks_beat_random_there():
    """Was: positive return in every regime, which for a long-only rule asks
    whether the market rose. A regime can be negative and still pass if the
    picks beat random names bought on those same days."""
    stats = summarize(result_of([trade(100)]))
    losing_but_better = {
        "bull_2017": RegimeResult("bull_2017", 50, +0.08, 80.0),
        "correction_2018q4": RegimeResult("correction_2018q4", 20, -0.06, 70.0),
        "bull_2019": RegimeResult("bull_2019", 50, +0.05, 20.0),
    }
    results = check_criteria(
        stats, effective_trades=500.0, regimes=losing_but_better,
        regime_buckets_in_split=3, same_day_p=0.001,
    )
    robustness = next(r for r in results if r.name == "regime_robustness")

    assert robustness.passed, "beat random in 2 of 3, worst -6%"
    assert "beat random in 2 of 3" in robustness.observed


def test_a_regime_losing_more_than_the_floor_still_fails():
    """Beating random does not excuse a 20% hole in a $10,000 account."""
    stats = summarize(result_of([trade(100)]))
    deep = {
        "bull_2017": RegimeResult("bull_2017", 50, +0.08, 90.0),
        "correction_2018q4": RegimeResult("correction_2018q4", 20, -0.20, 99.0),
        "bull_2019": RegimeResult("bull_2019", 50, +0.05, 95.0),
    }
    results = check_criteria(
        stats, effective_trades=500.0, regimes=deep,
        regime_buckets_in_split=3, same_day_p=0.001,
    )
    assert not next(r for r in results if r.name == "regime_robustness").passed


def test_a_regime_never_traded_counts_against_the_denominator():
    """Trading only the easy regime is not robustness. The denominator is the
    split's buckets, not the ones that happened to get trades."""
    stats = summarize(result_of([trade(100)]))
    one_only = {"bull_2017": RegimeResult("bull_2017", 50, +0.08, 99.0)}
    results = check_criteria(
        stats, effective_trades=500.0, regimes=one_only,
        regime_buckets_in_split=3, same_day_p=0.001,
    )
    assert not next(r for r in results if r.name == "regime_robustness").passed


def test_vs_random_reads_a_p_value_against_the_corrected_level():
    stats = summarize(result_of([trade(100)]))
    common = dict(effective_trades=500.0, regimes=regimes_of([trade(100)], percentile=90.0),
                  regime_buckets_in_split=3)

    single = check_criteria(stats, same_day_p=0.04, alpha=0.05, **common)
    corrected = check_criteria(stats, same_day_p=0.04, alpha=0.05 / 3, **common)

    assert next(r for r in single if r.name == "vs_random").passed
    assert not next(r for r in corrected if r.name == "vs_random").passed, \
        "p = 0.04 does not survive three tests sharing a 5% family"


# -- Holm --------------------------------------------------------------------

def test_holm_passes_only_what_survives_the_family():
    """Holm 1979: the k-th smallest p must clear alpha/(m-k), and the first
    failure stops every test above it."""
    from screener.backtest.performance import holm

    verdict = holm({"a": 0.004, "b": 0.02, "c": 0.30}, alpha=0.05)

    assert verdict["a"], "0.004 <= 0.05/3"
    assert verdict["b"], "0.02 <= 0.05/2"
    assert not verdict["c"]


def test_holm_stops_at_the_first_failure():
    """The step-down part. With three tests, 0.04 would clear the last step
    (0.05/1) on its own -- but 0.03 fails the middle step (0.05/2) first, and
    nothing above a failure passes."""
    from screener.backtest.performance import holm

    verdict = holm({"x": 0.001, "y": 0.03, "z": 0.04}, alpha=0.05)

    assert verdict["x"], "0.001 <= 0.05/3"
    assert not verdict["y"], "0.03 > 0.05/2"
    assert not verdict["z"], "blocked by y, despite 0.04 <= 0.05/1"


def test_a_single_test_is_held_to_the_plain_level():
    from screener.backtest.performance import holm

    assert holm({"only": 0.04}, alpha=0.05) == {"only": True}
