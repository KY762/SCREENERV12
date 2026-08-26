"""Value and quality ratios, hand-computed.

Every ratio returns None on missing input rather than substituting zero. Those
tests matter more than the arithmetic ones: a zero that reaches a ranking is
indistinguishable from a real measurement.
"""

from __future__ import annotations

from datetime import date

import pytest

from screener.fundamentals.pit import Reported
from screener.fundamentals.ratios import (
    accrual_ratio,
    book_value,
    current_ratio,
    gross_profitability,
    ncav_per_share,
    net_cash,
    net_current_asset_value,
    net_share_issuance,
    price_to_book,
    return_on_assets,
    snapshot,
)


def facts(**values) -> dict[str, Reported]:
    return {
        concept: Reported(
            concept, float(value), date(2023, 12, 31), date(2024, 2, 15), "acc", "USD"
        )
        for concept, value in values.items()
    }


def test_book_value_uses_equity_when_reported():
    assert book_value(facts(equity=500, assets=1000, liabilities=400)) == 500


def test_book_value_falls_back_to_assets_minus_liabilities():
    """Registrants tag equity inconsistently. Without a fallback, a third of
    companies silently drop out of a book-value screen."""
    assert book_value(facts(assets=1000, liabilities=400)) == 600


def test_book_value_is_none_when_neither_is_available():
    assert book_value(facts(cash=50)) is None


def test_price_to_book_by_hand():
    # equity 500 over 100 shares = 5.00 per share; price 10 -> P/B 2.0
    assert price_to_book(facts(equity=500, shares_outstanding=100), 10.0) == pytest.approx(2.0)


def test_price_to_book_is_none_on_negative_equity():
    """A negative book value produces a negative ratio that sorts to the top of
    a cheapness ranking, which is exactly backwards."""
    assert price_to_book(facts(equity=-200, shares_outstanding=100), 10.0) is None


def test_ncav_subtracts_total_liabilities_not_current_ones():
    """Graham's conservatism is the point of the measure. Using current
    liabilities would make almost anything look like a net-net."""
    got = net_current_asset_value(
        facts(assets_current=1000, liabilities_current=200, liabilities=700)
    )
    assert got == 300


def test_net_net_threshold_is_two_thirds_of_ncav():
    # NCAV 300 over 100 shares = 3.00; two-thirds = 2.00
    balance = facts(assets_current=1000, liabilities=700, shares_outstanding=100)

    assert snapshot("AAA", 1.99, balance).below_ncav
    assert not snapshot("AAA", 2.01, balance).below_ncav


def test_net_cash_is_cash_minus_all_liabilities():
    assert net_cash(facts(cash=900, liabilities=400)) == 500


def test_gross_profitability_by_hand():
    assert gross_profitability(facts(gross_profit=250, assets=1000)) == pytest.approx(0.25)


def test_gross_profitability_derives_from_revenue_when_not_reported_directly():
    got = gross_profitability(facts(revenue=800, cost_of_revenue=550, assets=1000))
    assert got == pytest.approx(0.25)


def test_accrual_ratio_is_positive_when_earnings_exceed_cash():
    """Profit you have not been paid for. Positive accruals are the warning."""
    earning_ahead = facts(net_income=100, operating_cash_flow=60, assets=1000)
    collecting_ahead = facts(net_income=60, operating_cash_flow=100, assets=1000)

    assert accrual_ratio(earning_ahead) == pytest.approx(0.04)
    assert accrual_ratio(collecting_ahead) == pytest.approx(-0.04)


def test_return_on_assets_and_current_ratio_by_hand():
    assert return_on_assets(facts(net_income=80, assets=1000)) == pytest.approx(0.08)
    assert current_ratio(facts(assets_current=600, liabilities_current=300)) == pytest.approx(2.0)


def test_division_by_zero_returns_none_rather_than_raising():
    assert return_on_assets(facts(net_income=80, assets=0)) is None
    assert current_ratio(facts(assets_current=600, liabilities_current=0)) is None
    assert gross_profitability(facts(gross_profit=250, assets=0)) is None


def test_net_share_issuance_is_negative_for_buybacks():
    now = facts(shares_outstanding=90)
    before = facts(shares_outstanding=100)
    assert net_share_issuance(now, before) == pytest.approx(-0.10)


def test_every_ratio_is_none_when_its_inputs_are_absent():
    empty: dict = {}
    assert ncav_per_share(empty) is None
    assert net_cash(empty) is None
    assert gross_profitability(empty) is None
    assert accrual_ratio(empty) is None
    assert net_share_issuance(empty, empty) is None


def test_snapshot_reports_which_filing_it_rests_on():
    """A surprising screen result has to be traceable to the numbers behind it."""
    snap = snapshot("AAA", 10.0, facts(equity=500, assets=1000, shares_outstanding=100))

    assert snap.reported_as_of == "2023-12-31"
    assert snap.lag_days == 46
