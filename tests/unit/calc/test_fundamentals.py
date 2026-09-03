"""Filings-derived signals computed from point-in-time facts.

The failure this file exists to catch is look-ahead. A fiscal period ends
months before the numbers are public and companies restate afterwards, so a
signal keyed on period_end, or one that silently picks up a later restatement,
is trading on information nobody had.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from screener.calc.fundamentals import (
    accruals,
    as_reported,
    asset_growth,
    latest,
    net_share_issuance,
    signal_frame,
)


def _facts(rows: list[tuple[str, str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "concept": concept,
                "period_end": date.fromisoformat(period_end),
                "filed": date.fromisoformat(filed),
                "value": value,
            }
            for concept, period_end, filed, value in rows
        ]
    )


ANNUAL = _facts([
    ("assets", "2023-12-31", "2024-02-20", 1_000.0),
    ("assets", "2024-12-31", "2025-02-18", 1_200.0),
    ("net_income", "2024-12-31", "2025-02-18", 100.0),
    ("operating_cash_flow", "2024-12-31", "2025-02-18", 60.0),
    ("shares_outstanding", "2023-12-31", "2024-02-20", 500.0),
    ("shares_outstanding", "2024-12-31", "2025-02-18", 525.0),
])


def test_a_fact_is_invisible_until_it_is_filed():
    """The period ended 2024-12-31 but nobody could read it until 2025-02-18.
    Keying on period_end instead of filed is the classic look-ahead bug and
    would make this return a value in January."""
    assert latest(ANNUAL, "assets", date(2025, 1, 15)).period_end == date(2023, 12, 31)
    assert latest(ANNUAL, "assets", date(2025, 2, 18)).period_end == date(2024, 12, 31)


def test_a_restatement_is_invisible_before_it_was_restated():
    """A later filing revises 2024 assets downward. A screen run in March must
    still see the originally reported figure -- the corrected number did not
    exist yet."""
    with_restatement = pd.concat([
        ANNUAL,
        _facts([("assets", "2024-12-31", "2025-08-01", 900.0)]),
    ], ignore_index=True)

    before = latest(with_restatement, "assets", date(2025, 3, 1))
    after = latest(with_restatement, "assets", date(2025, 9, 1))

    assert before.value == 1_200.0
    assert after.value == 900.0


def test_truncating_later_filings_does_not_change_earlier_answers():
    """The same invariant the price-side no-lookahead tests assert: what was
    computable on a date must not depend on anything filed after it."""
    later = pd.concat([
        ANNUAL,
        _facts([
            ("assets", "2025-12-31", "2026-02-17", 2_000.0),
            ("net_income", "2025-12-31", "2026-02-17", 400.0),
            ("operating_cash_flow", "2025-12-31", "2026-02-17", 50.0),
        ]),
    ], ignore_index=True)

    as_of = date(2025, 6, 1)
    assert accruals(later, as_of) == accruals(ANNUAL, as_of)
    assert asset_growth(later, as_of) == asset_growth(ANNUAL, as_of)


def test_accruals_are_income_less_cash_over_average_assets():
    """(100 - 60) / ((1200 + 1000) / 2) = 40 / 1100."""
    assert accruals(ANNUAL, date(2025, 3, 1)) == pytest.approx(40.0 / 1100.0)


def test_accruals_refuse_to_mix_fiscal_periods():
    """A full year of income against one quarter of cash flow is not an
    accrual, it is a units error that would look like enormous accruals."""
    mismatched = _facts([
        ("assets", "2023-12-31", "2024-02-20", 1_000.0),
        ("assets", "2024-12-31", "2025-02-18", 1_200.0),
        ("net_income", "2024-12-31", "2025-02-18", 100.0),
        ("operating_cash_flow", "2024-09-30", "2024-11-01", 15.0),
    ])

    assert accruals(mismatched, date(2025, 3, 1)) is None


def test_asset_growth_and_issuance_are_year_over_year_fractions():
    assert asset_growth(ANNUAL, date(2025, 3, 1)) == pytest.approx(0.20)
    assert net_share_issuance(ANNUAL, date(2025, 3, 1)) == pytest.approx(0.05)


def test_missing_inputs_return_none_rather_than_zero():
    """'Did not file' and 'filed a zero' are different companies. Imputing zero
    would rank a non-filer as though it had no accruals at all."""
    only_assets = _facts([("assets", "2024-12-31", "2025-02-18", 1_200.0)])

    assert accruals(only_assets, date(2025, 3, 1)) is None
    assert asset_growth(only_assets, date(2025, 3, 1)) is None
    assert net_share_issuance(only_assets, date(2025, 3, 1)) is None
    assert signal_frame(only_assets, date(2025, 3, 1)) == {
        "accruals": None, "asset_growth": None, "net_share_issuance": None,
    }


def test_a_gap_year_is_not_treated_as_year_over_year():
    """Comparing 2022 against 2024 and calling it annual growth doubles the
    measured change. Outside the tolerance the pair is rejected."""
    gapped = _facts([
        ("assets", "2022-12-31", "2023-02-20", 1_000.0),
        ("assets", "2024-12-31", "2025-02-18", 1_200.0),
    ])

    assert asset_growth(gapped, date(2025, 3, 1)) is None


def test_zero_denominator_returns_none_rather_than_dividing():
    degenerate = _facts([
        ("assets", "2023-12-31", "2024-02-20", 0.0),
        ("assets", "2024-12-31", "2025-02-18", 1_200.0),
    ])

    assert asset_growth(degenerate, date(2025, 3, 1)) is None


def test_no_facts_at_all_is_empty_not_an_error():
    empty = pd.DataFrame(columns=["concept", "period_end", "filed", "value"])

    assert as_reported(empty, "assets", date(2025, 3, 1)) == []
    assert latest(empty, "assets", date(2025, 3, 1)) is None
