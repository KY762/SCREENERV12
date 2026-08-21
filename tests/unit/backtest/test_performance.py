"""Statistics with hand-computed expected values."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from screener.backtest.engine import BacktestResult, Trade
from screener.backtest.performance import (
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


def test_criteria_fail_on_trade_count_even_when_everything_else_is_good():
    stats = summarize(result_of([trade(200), trade(200), trade(-100)]))
    results = check_criteria(stats, by_regime([trade(200), trade(200), trade(-100)]))

    by_name = {r.name: r for r in results}
    assert by_name["expectancy"].passed
    assert by_name["profit_factor"].passed
    assert not by_name["trade_count"].passed
    assert not all_passed(results)


def test_missing_random_benchmark_counts_as_a_failure_not_a_skip():
    """A criterion that was never measured has not been met."""
    stats = summarize(result_of([trade(100)]))
    results = check_criteria(stats, {}, random_percentile=None)
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

    results = check_criteria(stats, by_regime(trades, 10_000))
    robustness = next(r for r in results if r.name == "regime_robustness")

    assert "-1.0%" in robustness.observed
