"""Risk and sizing tests.

These encode the Risk Manager veto conditions from the trader profile (7.1).
Each maps to a documented failure in the operator's journal, so a regression
here is not a cosmetic bug -- it re-opens a known way of losing money.
"""

from decimal import Decimal

import pytest

from screener.calc.sizing import RiskLimits, plan_position


def test_basic_sizing_golden():
    """equity 10,000 at 1% -> 100 risk budget.
    entry 50.00, stop 47.00 -> risk/share 3.00 -> floor(100/3) = 33 shares.
    position value 33 x 50 = 1,650 = 16.5% of equity, inside the 25% cap.
    actual risk 33 x 3 = 99.00 (not 100 -- shares are whole).
    """
    p = plan_position(equity=10_000, entry=50, stop=47)
    assert p.shares == 33
    assert p.risk_per_share == Decimal("3")
    assert p.risk_dollars == Decimal("99.00")
    assert p.position_value == Decimal("1650.00")
    assert p.position_pct_of_equity == Decimal("0.165")
    assert p.is_tradeable


def test_concentration_cap_reduces_shares_and_never_widens_the_stop():
    """A tight stop implies a large position: risk/share 0.50 -> 200 shares ->
    $20,000, which is 200% of equity. The cap must cut shares to 25 ($2,500)
    and leave the stop exactly where it was.

    This is the single most important invariant in the module. Widening a stop
    to fit a desired size is the mechanism behind 'I switched to NQ and started
    balling'.
    """
    p = plan_position(equity=10_000, entry=100, stop=Decimal("99.50"))
    assert p.shares == 25
    assert p.stop == Decimal("99.50"), "stop was modified to accommodate size"
    assert p.position_value == Decimal("2500.00")
    assert any("size reduced" in r for r in p.reasons)
    assert p.is_tradeable, "a size reduction is not a rejection"


@pytest.mark.parametrize(
    "entry,stop",
    [(50, 55), (50, 50), (50, 0), (0, -1)],
)
def test_invalid_stop_is_rejected(entry, stop):
    p = plan_position(equity=10_000, entry=entry, stop=stop)
    assert p.rejected
    assert p.shares == 0
    assert p.reasons


def test_stop_is_never_altered_across_a_wide_input_sweep():
    """Property check: whatever the constraints do, the stop comes back untouched."""
    for entry_cents in range(500, 20_000, 617):
        entry = Decimal(entry_cents) / 100
        for pct in ("0.001", "0.01", "0.05", "0.20"):
            stop = (entry * (1 - Decimal(pct))).quantize(Decimal("0.01"))
            if stop <= 0:
                continue
            p = plan_position(equity=10_000, entry=entry, stop=stop)
            assert p.stop == stop, f"stop mutated for entry={entry} stop={stop}"


def test_max_concurrent_positions_blocks_entry():
    p = plan_position(equity=10_000, entry=50, stop=47, open_positions=5)
    assert p.rejected
    assert any("max concurrent positions" in r for r in p.reasons)


def test_sector_limit_blocks_entry():
    p = plan_position(equity=10_000, entry=50, stop=47, sector_positions=2)
    assert p.rejected
    assert any("max positions per sector" in r for r in p.reasons)


def test_total_open_risk_cap_blocks_entry():
    """Four positions already risking 1% each, plus this one, stays inside 5%.
    At 4.5% already committed, the fifth would breach it."""
    ok = plan_position(equity=10_000, entry=50, stop=47, open_risk_pct=Decimal("0.04"))
    assert ok.is_tradeable

    blocked = plan_position(equity=10_000, entry=50, stop=47, open_risk_pct=Decimal("0.045"))
    assert blocked.rejected
    assert any("total open risk" in r for r in blocked.reasons)


def test_r_multiple_golden_and_minimum_enforced():
    """entry 50, stop 47 -> risk 3. target 59 -> reward 9 -> R = 3.00."""
    p = plan_position(equity=10_000, entry=50, stop=47, target=59)
    assert p.r_multiple_to_target == Decimal("3.00")
    assert p.is_tradeable

    thin = plan_position(equity=10_000, entry=50, stop=47, target=53, min_r_multiple=2)
    assert thin.r_multiple_to_target == Decimal("1.00")
    assert thin.rejected
    assert any("below the 2 minimum" in r for r in thin.reasons)


def test_target_below_entry_is_rejected():
    p = plan_position(equity=10_000, entry=50, stop=47, target=49)
    assert p.rejected
    assert any("target must be above entry" in r for r in p.reasons)


def test_risk_budget_too_small_for_one_share():
    """A $200 account at 1% has $2 of risk. A stop $5 away buys nothing --
    and the plan says so rather than silently returning zero."""
    p = plan_position(equity=200, entry=100, stop=95)
    assert p.shares == 0
    assert p.rejected
    assert any("too small for one share" in r for r in p.reasons)


def test_custom_limits_are_honoured():
    tight = RiskLimits(risk_pct_per_trade=Decimal("0.005"), max_position_pct=Decimal("0.10"))
    p = plan_position(equity=10_000, entry=50, stop=47, limits=tight)
    assert p.shares == 16          # floor(50 / 3)
    assert p.risk_dollars == Decimal("48.00")


def test_rejected_plan_still_reports_its_numbers():
    """A rejection is information. The caller should be able to show the operator
    what the trade WOULD have been and exactly which rule stopped it."""
    p = plan_position(equity=10_000, entry=50, stop=47, open_positions=5)
    assert p.rejected
    assert p.shares > 0
    assert p.position_value > 0
    assert p.reasons
