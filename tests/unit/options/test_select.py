"""Contract selection and cost accounting.

The rules encoded here are the argument for using options at all. Each test
describes a way the default retail choice loses money and asserts the selector
refuses it.
"""

from __future__ import annotations

from datetime import date

import pytest

from screener.options.contracts import OptionContract, build_occ, parse_occ
from screener.options.select import (
    SelectionRules,
    choose_contract,
    eligible_contracts,
    plan_option_trade,
)

TODAY = date(2026, 8, 26)


def contract(strike, expiry, *, bid=10.0, ask=10.2, delta=0.75, theta=-0.05,
             oi=5000, volume=500, right="C", underlying="AAA") -> OptionContract:
    return OptionContract(
        symbol=build_occ(underlying, expiry, right, strike),
        underlying=underlying, expiry=expiry, strike=strike, right=right,
        bid=bid, ask=ask, delta=delta, theta=theta,
        open_interest=oi, volume=volume,
    )


# -- OCC ---------------------------------------------------------------------

def test_occ_round_trips():
    symbol = build_occ("AAPL", date(2026, 1, 16), "C", 150.0)
    parsed = parse_occ(symbol)

    assert symbol == "AAPL260116C00150000"
    assert (parsed.underlying, parsed.expiry, parsed.strike, parsed.right) == (
        "AAPL", date(2026, 1, 16), 150.0, "C"
    )


def test_occ_handles_fractional_strikes():
    """A strike parsed as 7.5 when it is 75.0 buys the wrong contract and
    raises no exception."""
    assert parse_occ(build_occ("F", date(2026, 3, 20), "C", 7.5)).strike == 7.5
    assert parse_occ(build_occ("F", date(2026, 3, 20), "C", 12.25)).strike == 12.25


def test_malformed_occ_returns_none():
    assert parse_occ("GARBAGE") is None
    assert parse_occ("AAPL261301C00150000") is None      # month 13


# -- eligibility -------------------------------------------------------------

def test_an_expiry_inside_the_hold_is_rejected():
    """Decay accelerates into expiry. Buying 10 days of option for a 10-day
    trade pays the steepest part of the curve with no room to be late."""
    near = contract(90, date(2026, 9, 2))       # 7 days out
    far = contract(90, date(2026, 10, 30))      # 65 days out

    kept, dropped = eligible_contracts([near, far], as_of=TODAY, hold_days=10)

    assert kept == [far]
    assert any("expires inside" in reason for reason in dropped)


def test_a_contract_spanning_earnings_is_rejected():
    """Two separate losses: the gap, and implied volatility collapsing after
    the report — which loses money even when the direction is right."""
    spanning = contract(90, date(2026, 10, 30))

    kept, dropped = eligible_contracts(
        [spanning], as_of=TODAY, hold_days=10, earnings_in_days=20
    )

    assert kept == []
    assert dropped.get("spans earnings") == 1


def test_a_wide_spread_is_rejected():
    """8% wide is 16% round trip, before the trade is right or wrong."""
    wide = contract(90, date(2026, 10, 30), bid=9.0, ask=9.8)

    kept, dropped = eligible_contracts([wide], as_of=TODAY, hold_days=10)

    assert kept == []
    assert any("spread wider" in reason for reason in dropped)


def test_illiquid_contracts_are_rejected():
    thin = contract(90, date(2026, 10, 30), oi=12)

    kept, _ = eligible_contracts([thin], as_of=TODAY, hold_days=10)
    assert kept == []


def test_a_one_sided_market_is_rejected():
    no_bid = contract(90, date(2026, 10, 30), bid=0.0, ask=9.0)

    kept, dropped = eligible_contracts([no_bid], as_of=TODAY, hold_days=10)
    assert kept == []
    assert dropped.get("no two-sided market") == 1


def test_low_delta_contracts_are_rejected():
    """An out-of-the-money call is a bet on speed as well as direction, and
    nothing here forecasts speed."""
    lottery = contract(130, date(2026, 10, 30), bid=0.9, ask=0.92, delta=0.12)

    kept, dropped = eligible_contracts([lottery], as_of=TODAY, hold_days=10)
    assert kept == []
    assert dropped.get("delta outside range") == 1


def test_puts_are_excluded_from_a_long_screen():
    put = contract(90, date(2026, 10, 30), right="P")
    kept, _ = eligible_contracts([put], as_of=TODAY, hold_days=10)
    assert kept == []


# -- choice ------------------------------------------------------------------

def test_the_contract_closest_to_the_target_delta_wins():
    chain = [
        contract(70, date(2026, 10, 30), delta=0.92),
        contract(85, date(2026, 10, 30), delta=0.76),
        contract(95, date(2026, 10, 30), delta=0.62),
    ]

    chosen = choose_contract(chain, as_of=TODAY, hold_days=10)
    assert chosen.strike == 85


def test_nearest_qualifying_expiry_wins_on_a_delta_tie():
    """Once expiry clears the hold with margin, more time is more premium for
    nothing."""
    chain = [
        contract(85, date(2026, 12, 18), delta=0.75),
        contract(85, date(2026, 10, 16), delta=0.75),
    ]

    assert choose_contract(chain, as_of=TODAY, hold_days=10).expiry == date(2026, 10, 16)


def test_no_eligible_contract_returns_none_rather_than_the_least_bad():
    chain = [contract(90, date(2026, 8, 28))]      # expires in 2 days
    assert choose_contract(chain, as_of=TODAY, hold_days=10) is None


# -- sizing and costs --------------------------------------------------------

def test_sizing_uses_the_move_to_the_stop_not_the_whole_premium():
    """Treating the full premium as the risk overstates it and produces
    positions too small to matter, which is its own failure mode."""
    call = contract(90, date(2026, 10, 30), bid=12.0, ask=12.2, delta=0.75, theta=-0.04)

    plan = plan_option_trade(
        call, underlying_price=100.0, stop_price=96.0, hold_days=10,
        risk_budget=500.0, cash_available=10_000.0, as_of=TODAY,
    )

    # 0.75 delta x $4 stop distance x 100 = $300 directional, plus spread and decay.
    assert plan.stop_loss_estimate == pytest.approx(300.0, abs=1.0)
    assert plan.contracts >= 1


def test_every_cost_is_reported_separately():
    call = contract(90, date(2026, 10, 30), bid=12.0, ask=12.4, delta=0.75, theta=-0.05)

    plan = plan_option_trade(
        call, underlying_price=100.0, stop_price=96.0, hold_days=10,
        risk_budget=1000.0, cash_available=10_000.0, as_of=TODAY,
    )

    assert plan.spread_cost > 0, "the spread is paid twice and must be visible"
    assert plan.decay_cost > 0, "theta accrues whether or not the thesis works"
    assert plan.friction_pct > 0


def test_a_mostly_time_value_contract_is_rejected_with_its_reason():
    """The default retail choice. Most of the premium evaporates on schedule."""
    call = contract(105, date(2026, 10, 30), bid=3.0, ask=3.1, delta=0.62, theta=-0.06)

    plan = plan_option_trade(
        call, underlying_price=100.0, stop_price=96.0, hold_days=10,
        risk_budget=1000.0, cash_available=10_000.0, as_of=TODAY,
    )

    assert not plan.is_tradeable
    assert any("time value" in reason for reason in plan.rejections)


def test_cash_constrains_the_position_even_when_risk_does_not():
    call = contract(90, date(2026, 10, 30), bid=12.0, ask=12.2, delta=0.75, theta=-0.04)

    plan = plan_option_trade(
        call, underlying_price=100.0, stop_price=96.0, hold_days=10,
        risk_budget=100_000.0, cash_available=2_500.0, as_of=TODAY,
    )

    assert plan.cost <= 2_500.0


def test_the_stock_alternative_is_always_shown():
    """The comparison is the point. An option plan without the shares it
    replaces hides what is being given up."""
    call = contract(90, date(2026, 10, 30), bid=12.0, ask=12.2, delta=0.75, theta=-0.04)

    plan = plan_option_trade(
        call, underlying_price=100.0, stop_price=96.0, hold_days=10,
        risk_budget=500.0, cash_available=10_000.0, as_of=TODAY,
    )

    assert plan.shares_equivalent == 125       # $500 risk / $4 stop distance
    assert plan.breakeven > plan.stock_breakeven, (
        "the option needs a bigger move than the stock to break even"
    )


def test_leverage_is_computed_so_it_can_be_looked_at():
    call = contract(90, date(2026, 10, 30), bid=12.0, ask=12.2, delta=0.75)

    plan = plan_option_trade(
        call, underlying_price=100.0, stop_price=96.0, hold_days=10,
        risk_budget=500.0, cash_available=10_000.0, as_of=TODAY,
    )

    assert plan.effective_leverage == pytest.approx(6.2, abs=0.3)


def test_rules_are_adjustable_without_editing_the_module():
    strict = SelectionRules(max_spread_pct=0.01)
    call = contract(90, date(2026, 10, 30), bid=10.0, ask=10.2)

    assert eligible_contracts([call], as_of=TODAY, hold_days=10)[0] == [call]
    assert eligible_contracts([call], as_of=TODAY, hold_days=10, rules=strict)[0] == []
