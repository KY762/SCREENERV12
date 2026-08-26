"""Whether an account can express a normal position in a given stock.

Both failure modes are arithmetic and neither has anything to do with the
company, which is why they are easy to miss: the chart looks fine.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from screener.calc.sizing import RiskLimits
from screener.calc.tradeability import (
    assess,
    max_workable_price,
    min_workable_atr_pct,
)


def test_a_cheap_volatile_stock_sizes_cleanly():
    """$27 stock, ~4% ATR: 46 shares, cap never binds, risk lands on target."""
    result = assess("INTC", 27.14, 27.14 * 0.0392)

    assert result.verdict == "good"
    assert result.shares > 40
    assert result.precision == pytest.approx(1.0, abs=0.05)
    assert not result.concentration_capped


def test_an_expensive_stock_is_unusable_at_this_size():
    """$949 with a $26 stop is 3 shares. Rounding throws away a third of the
    intended risk and there is nothing left to tune."""
    result = assess("COST", 948.73, 948.73 * 0.0138)

    assert result.verdict == "unusable"
    assert result.shares <= 3
    assert any("rounding" in reason for reason in result.reasons)


def test_a_share_count_problem_disappears_on_a_larger_account():
    """A $900 stock with a wide stop is one share at $10k and a real position
    at $100k. Nothing about the company changed."""
    small = assess("PRICEY", 900.0, 900.0 * 0.03, equity=10_000)
    large = assess("PRICEY", 900.0, 900.0 * 0.03, equity=100_000)

    assert small.verdict == "unusable"
    assert large.verdict == "good"


def test_a_cap_problem_does_NOT_disappear_on_a_larger_account():
    """The two failure modes are not the same, and this is the difference.

    Share granularity is about account size. The cap binding is about the ratio
    of risk-per-trade to the concentration limit versus the stock's volatility
    -- so a 1.4% ATR name risks 0.68% instead of 1% at every account size, and
    more money never fixes it. Only a different stock, or different limits, do.
    """
    verdicts = {
        equity: assess("COST", 948.73, 948.73 * 0.0138, equity=equity)
        for equity in (10_000, 100_000, 1_000_000)
    }

    for equity, result in verdicts.items():
        assert result.concentration_capped, f"cap should bind at {equity}"
    assert verdicts[100_000].precision == pytest.approx(
        verdicts[1_000_000].precision, abs=0.01
    )


def test_a_low_volatility_stock_trips_the_concentration_cap():
    """A tight stop buys a large position for the same risk, the cap cuts it,
    and the trade quietly risks less than the rule says."""
    result = assess("LOWVOL", 100.0, 1.00)      # 1% ATR

    assert result.concentration_capped
    assert result.effective_risk_pct < result.intended_risk_pct
    assert any("concentration cap" in reason for reason in result.reasons)


def test_the_cap_reduces_risk_rather_than_increasing_it():
    """Worth asserting explicitly: capping is conservative. The problem is that
    the sizing rule stops describing what happens, not that it is dangerous."""
    result = assess("LOWVOL", 100.0, 1.00)
    assert result.precision < 1.0


def test_precision_reports_how_far_realised_risk_missed_the_target():
    result = assess("AAPL", 313.29, 313.29 * 0.0172)

    assert 0 < result.precision < 1
    assert result.effective_risk_pct == pytest.approx(
        result.intended_risk_pct * result.precision, rel=1e-6
    )


def test_marginal_sits_between_good_and_unusable():
    good = assess("A", 27.0, 27.0 * 0.04)
    marginal = assess("B", 186.0, 186.0 * 0.028)
    unusable = assess("C", 949.0, 949.0 * 0.014)

    assert [good.verdict, marginal.verdict, unusable.verdict] == [
        "good", "marginal", "unusable"
    ]


def test_thresholds_follow_the_risk_limits_rather_than_being_hardcoded():
    """Halving risk per trade halves the share count, which changes the
    verdict. The assessment has to read the limits, not assume them."""
    tight = RiskLimits(risk_pct_per_trade=Decimal("0.005"))
    at_one_pct = assess("X", 150.0, 150.0 * 0.025)
    at_half_pct = assess("X", 150.0, 150.0 * 0.025, limits=tight)

    assert at_half_pct.shares < at_one_pct.shares


def test_a_wider_stop_reduces_the_share_count():
    narrow = assess("X", 100.0, 2.0, stop_atr=1.0)
    wide = assess("X", 100.0, 2.0, stop_atr=4.0)

    assert wide.shares < narrow.shares


def test_nonsense_inputs_are_rejected_rather_than_computed():
    assert assess("X", 0, 1.0).verdict == "unusable"
    assert assess("X", 100.0, 0).verdict == "unusable"
    assert assess("X", 100.0, 2.0, equity=0).verdict == "unusable"


def test_price_ceiling_matches_the_share_requirement():
    """At 2% ATR and a 2-ATR stop, $100 of risk buys 10 shares only up to $250."""
    assert max_workable_price(0.02) == pytest.approx(250.0)
    assert assess("X", 250.0, 250.0 * 0.02).shares == 10
    assert assess("X", 260.0, 260.0 * 0.02).shares < 10


def test_volatility_floor_matches_the_cap():
    """Below 2% ATR the cap binds, at or above it does not. Independent of
    price, which is what makes it usable as a universe filter."""
    floor = min_workable_atr_pct()
    assert floor == pytest.approx(0.02)

    assert not assess("X", 100.0, 100.0 * floor).concentration_capped
    assert assess("X", 100.0, 100.0 * (floor - 0.005)).concentration_capped
